"""One public OpenRouter review per dispatch; Git CAS reserves before transport.

This worker never promotes designs. Legacy workers remain disabled. All admitted
calls use the one Garden Actions key and the same state branch. UNKNOWN attempts
require reconciliation; a new run cannot silently retry them.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import time
from urllib import request, error

from tools import matrix_design_review as review
from tools.provider_exclusion import load_policy, require_allowed_model, excluded_provider_slugs

REPO = 'ankitdcx/garden-swarm'
STATE_BRANCH = 'garden-review-state'
STATE_PATH = 'review-state/ledger.json'
API = 'https://api.github.com/repos/' + REPO
OR = 'https://openrouter.ai/api/v1'
SCHEMA = 'GardenSingleReviewLedger/v1'
ROUNDS = ('BLIND', 'CHALLENGE', 'REVISE', 'VERIFY')


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def money(value):
    if isinstance(value, bool) or value is None:
        raise ValueError('unknown monetary value')
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('invalid monetary value') from exc
    if not number.is_finite() or number < 0:
        raise ValueError('invalid monetary value')
    return number


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('HTTP redirects refused')


def http(url, token, body=None, method=None, timeout=30):
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
               'Accept': 'application/json', 'User-Agent': 'Garden-single-review-worker'}
    req = request.Request(url, data=None if body is None else encode(body).encode(),
                          headers=headers, method=method or ('POST' if body is not None else 'GET'))
    # No retry, fallback or redirect may create a second inference request.
    with request.build_opener(NoRedirect()).open(req, timeout=timeout) as response:
        return json.loads(response.read(2_000_001))


class GitLedger:
    def __init__(self, token):
        self.token = token
        result = http(API + '/contents/' + STATE_PATH + '?ref=' + STATE_BRANCH, token)
        self.sha = result['sha']
        self.value = json.loads(base64.b64decode(result['content']))
        if self.value.get('schema') != SCHEMA or self.value.get('repository') != REPO:
            raise ValueError('unrecognized ledger; automatic initialization refused')

    def save(self, value):
        result = http(API + '/contents/' + STATE_PATH, self.token, {
            'message': 'Record single-review execution state', 'branch': STATE_BRANCH,
            'sha': self.sha, 'content': base64.b64encode((encode(value) + '\n').encode()).decode(),
        }, method='PUT')
        # Failed/ambiguous CAS is never retried and never authorizes inference.
        self.sha = result['content']['sha']
        self.value = value


def next_slot(cycle, families):
    for round_no in range(len(ROUNDS)):
        for family in families:
            key = f'{round_no}:{family}'
            if key not in cycle:
                return round_no, family, key
            if cycle[key].get('status') != 'REVIEW_RECORDED':
                raise ValueError('prior attempt unresolved; reconciliation required')
        if round_no == 1 and all(cycle[f'1:{f}']['finding']['disposition'] == 'NO_CHANGE' for f in families):
            return None  # Stop debate; does not prove or admit anything.
    return None


def budget_check(state, key_info, policy, now):
    if state.get('paused') is not False:
        raise ValueError('single worker paused')
    if any(a['status'] in ('RESERVED', 'UNKNOWN') for a in state['attempts']):
        raise ValueError('outstanding reservation/unknown cost; reconciliation required')
    if key_info.get('is_management_key') is True or key_info.get('is_free_tier') is True:
        raise ValueError('paid inference key required')
    usage = money(key_info.get('usage'))
    daily = money(key_info.get('usage_daily'))
    reserve = min(money(policy['routine_model_call_cost_ceiling_usd']), Decimal('0.05'))
    ceiling = min(money(policy['daily_openrouter_cost_ceiling_usd']), Decimal('1'))
    day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
    current = [a for a in state['attempts'] if a['utc_day'] == day]
    # Conservatively count known old account spend plus local spend, even where
    # provider totals already include it. This tolerates delayed usage reporting.
    baseline = max([daily] + [money(a['usage_daily_before']) for a in current])
    spent = sum((money(a['cost']) for a in current), Decimal(0))
    if baseline + spent + reserve > ceiling:
        raise ValueError('daily reservation exhausted')
    # Charge all historical key spend against the routine pool, conservatively;
    # no access to challenger/escalation/emergency funds is granted here.
    routine = money(policy['budget_pools_usd']['routine'])
    all_spent = sum((money(a['cost']) for a in state['attempts']), Decimal(0))
    if usage + all_spent + reserve > routine:
        raise ValueError('routine lifetime allocation exhausted')
    remaining = key_info.get('limit_remaining')
    if remaining is not None and money(remaining) < reserve:
        raise ValueError('key credit limit too low')
    return reserve, day, str(daily)


def endpoint_request(endpoint, model, prompt, reserve, policy, exclusions):
    tag, name = endpoint.get('tag'), endpoint.get('provider_name')
    if not tag or not name or endpoint.get('status') != 0:
        raise ValueError('endpoint unavailable or unidentified')
    require_allowed_model(model_id=model['model'], family=model['family'], policy=exclusions)
    require_allowed_model(model_id=tag + '/' + name, family=name, policy=exclusions)
    if tag.split('/')[0].lower() in excluded_provider_slugs(exclusions):
        raise ValueError('excluded endpoint')
    pricing = endpoint['pricing']
    cap = policy['provider_policy']['max_price_usd_per_million_tokens']
    pin, pout = money(pricing['prompt']), money(pricing['completion'])
    if pin * 1_000_000 > money(cap['prompt']) or pout * 1_000_000 > money(cap['completion']):
        raise ValueError('endpoint above routing price cap')
    if any(money(v) != 0 for k, v in pricing.items() if k not in ('prompt', 'completion', 'input_cache_read', 'input_cache_write')):
        raise ValueError('additional endpoint fees unsupported')
    # UTF-8 bytes plus framing margin is a conservative bound for the approved
    # text tokenizers. Reject if bound or context cannot be satisfied.
    prompt_bound = len(prompt.encode()) + 4096
    output = min(int(policy['max_output_tokens']), 1800)
    estimated = prompt_bound * pin + output * pout
    if estimated > reserve or prompt_bound + output > int(endpoint['context_length']):
        raise ValueError('request exceeds reserved cost/context')
    if len(prompt) > min(int(policy['max_prompt_characters']), 60000):
        raise ValueError('context too large; no silent truncation')
    body = {'model': model['model'], 'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': output, 'temperature': 0.1, 'stream': False,
            'provider': {'only': [tag], 'allow_fallbacks': False, 'require_parameters': True,
                         'data_collection': 'deny', 'zdr': True,
                         'ignore': excluded_provider_slugs(exclusions),
                         'max_price': {'prompt': str(pin * 1_000_000), 'completion': str(pout * 1_000_000)}}}
    return body, str(estimated)


def run(root=Path('.')):
    if os.environ.get('GITHUB_REPOSITORY') != REPO or os.environ.get('GITHUB_REF') != 'refs/heads/main':
        raise ValueError('only the installed main-branch worker may dispatch')
    if os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        raise ValueError('explicit scoped dispatch required')
    key, gh = os.environ.get('OPENROUTER_API_KEY'), os.environ.get('GH_REVIEW_TOKEN')
    if not key or not gh:
        raise ValueError('required Actions secret/token unavailable')
    state_store = GitLedger(gh)
    state = state_store.value
    if state.get('scope') != 'PUBLIC_MATRIX_REVIEW_ONLY':
        raise ValueError('ledger scope mismatch')
    policy = json.loads((root / 'agents/openrouter-paid-review-policy.json').read_text())
    exclusions = load_policy(root / 'agents/provider-exclusion-policy.json')
    matrix, target = review.load_matrix(root)
    source, trace = review.extract_target(root, target)
    manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
    expected = {f['path']: f['sha256'] for f in manifest['canonical_files']}
    if expected.get(trace['source']) != trace['source_sha256']:
        raise ValueError('source is not the pinned public canonical file')
    families = [m['family'] for m in policy['routine_reviewers']]
    if len(set(families)) < 3 or len(set(families)) != len(families):
        raise ValueError('distinct allocated reviewer families required')
    binding = {'trace': trace, 'target': target, 'policy_hash': digest(policy),
               'worker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'exclusions_hash': digest(exclusions), 'design_epoch': matrix['design_epoch']}
    cycle_id = digest(binding)
    cycle = state['cycles'].setdefault(cycle_id, {})
    slot = next_slot(cycle, families)
    if slot is None:
        print('REVIEW_ROUNDS_FINISHED_PROPOSALS_ONLY; tests and integration still required')
        return
    round_no, family, slot_key = slot
    model = next(m for m in policy['routine_reviewers'] if m['family'] == family)
    prompt = review.independent_prompt(target=target, source=source, trace=trace, model=model)
    if round_no:
        prior = [cycle[f'{round_no-1}:{f}']['finding'] for f in families]
        prompt = prompt.replace('You have not seen and must not infer any peer conclusion.',
                                'This is a follow-up; challenge evidence rather than vote.')
        prompt += '\nROUND: ' + ROUNDS[round_no] + '\nPrior findings (untrusted proposals):\n' + encode(prior)
        prompt += '\nName each unresolved issue, respond to peer objections, and give a falsifiable test. Never claim a test ran without evidence.'
    key_info = http(OR + '/key', key)['data']
    reserve, day, daily = budget_check(state, key_info, policy, time.time())
    endpoints = http(OR + '/models/' + model['model'] + '/endpoints', key)['data']['endpoints']
    eligible = []
    for endpoint in endpoints:
        try:
            body, estimate = endpoint_request(endpoint, model, prompt, reserve, policy, exclusions)
            eligible.append((money(estimate), endpoint, body))
        except (ValueError, KeyError, RuntimeError):
            continue
    if not eligible:
        raise ValueError('no permitted, affordable live endpoint; no model substitution')
    estimate, endpoint, body = min(eligible, key=lambda row: row[0])
    attempt = {'status': 'RESERVED', 'cycle': cycle_id, 'slot': slot_key, 'round': ROUNDS[round_no],
               'model': model['model'], 'family': family, 'endpoint': endpoint['tag'],
               'binding': binding, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
               'source_commit': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
               'utc_day': day, 'started': time.time(), 'usage_daily_before': daily,
               'reserved': str(reserve), 'estimated_upper_cost': str(estimate), 'cost': None,
               'semantic_delta_admitted': False, 'full_review_complete': False}
    state['attempts'].append(attempt)
    cycle[slot_key] = attempt
    state_store.save(state)  # Durable compare-and-swap BEFORE the sole model call.
    try:
        response = http(OR + '/chat/completions', key, body, timeout=90)
        attempt.update(response_id=response.get('id'), actual_model=response.get('model'),
                       actual_provider=response.get('provider'), usage=response.get('usage'))
        choices = response.get('choices') or []
        if choices:
            attempt['response_text'] = choices[0].get('message', {}).get('content')
        cost = money(response.get('usage', {}).get('cost'))
        attempt.update(cost=str(cost), response_id=response.get('id'), actual_model=response.get('model'),
                       actual_provider=response.get('provider'), usage=response.get('usage'))
        if cost > reserve:
            raise ValueError('cost exceeds reservation')
        if response.get('model') != model['model'] or response.get('provider') != endpoint['provider_name']:
            raise ValueError('returned model/provider identity mismatch')
        if not response.get('id'):
            raise ValueError('provider response identity missing')
        choice = response['choices'][0]
        content = choice['message'].get('content', '')
        attempt['response_text'] = content
        if choice.get('finish_reason') != 'stop':
            raise ValueError('review incomplete/truncated')
        finding = review.validate_independent(review._clean_json(content), target_id=target['target_id'],
                                              family=family, model_id=model['model'])
        finding['independent'] = round_no == 0
        attempt.update(status='REVIEW_RECORDED', finding=finding)
    except Exception as exc:
        # No exception body or headers: upstream errors can contain secret data.
        attempt.update(status='UNKNOWN', error_type=type(exc).__name__)
    out = root / 'agents/outbox/single-review/receipt.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(encode(attempt) + '\n')
    state_store.save(state)  # Failure leaves the durable RESERVED state in place.
    print(attempt['status'] + ': ' + family + ' ' + ROUNDS[round_no] + '; proposal evidence only')
    if attempt['status'] != 'REVIEW_RECORDED':
        raise SystemExit(2)


if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        # No key, headers, raw provider error bodies or private account metadata.
        print('REVIEW_BLOCKED: ' + type(exc).__name__ + ': ' +
              (str(exc) if isinstance(exc, ValueError) else 'see saved state/receipt; no automatic retry'))
        raise SystemExit(2)
