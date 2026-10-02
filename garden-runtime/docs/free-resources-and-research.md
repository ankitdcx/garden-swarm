# Legitimate resources and implementation research

Checked: 2026-10-02. Status: research input, not canonical Garden semantics. No paid model call, OpenRouter request, promotional account, quota evasion or grant application was made. Quotas are provider policy and must be rechecked before scaling.

## Resource routes

| Route | Verified terms/limits | Fit and current boundary |
|---|---|---|
| GitHub public repository + standard Actions | Standard hosted runners are free for public repositories; hosted job maximum 6 hours; Free standard concurrency 20 jobs, of which 5 macOS | CI/build/model smoke; not a continuously hosted inference service. Larger runners can cost money. |
| GitHub Pages | Static deployment | Console/receipt viewer; no live Rust gate or Python inference by itself. |
| Hugging Face CPU Basic | 2 vCPU, 16 GB RAM, 50 GB disk, zero hourly hardware rate; new Gradio/Docker compute Spaces require a paid plan | Do not mistake zero hourly price for unconditional free account eligibility. Static Spaces remain free. |
| Hugging Face ZeroGPU | Free personal accounts with verified email, age over 30 days and good standing can host 2 Spaces; Gradio only; anonymous 2 GPU minutes/day, free account 5 minutes/day; reset exactly 24 hours after first usage | Account authorization needed. Default half RTX Pro 6000 Blackwell has 48 GB; full 96 GB uses twice the quota. Queues/finite quota prevent always-on inference. |
| Hugging Face public model/dataset storage | Free public storage best effort; private Free quota 100 GB | Public model hosting, not unlimited entitlement. Use immutable weight revisions and hashes. |
| Hugging Face community GPU grant | Application via an existing Space's hardware settings; acceptance discretionary | Prepared application can be useful after a working demo, but no grant/compute allocation is claimed. |
| Google Colab Free | Resources and GPU access are not guaranteed; limits fluctuate and exact quotas are not published | Human notebook experiments; not dependable autonomous backend. No quota-evasion/idle-bypass workarounds. |
| Existing workspace CPU | Actual local inference/build available; no extra purchase made | Session persistence/availability is unspecified. The host must establish model/gate isolation before enabling consequential actions. |

Primary sources: [GitHub billing](https://docs.github.com/en/actions/concepts/billing-and-usage), [GitHub limits](https://docs.github.com/en/actions/reference/limits), [HF GPU/CPU Spaces](https://huggingface.co/docs/hub/en/spaces-gpus), [HF ZeroGPU](https://huggingface.co/docs/hub/en/spaces-zerogpu), [HF storage](https://huggingface.co/docs/hub/en/storage-limits), [Colab FAQ](https://research.google.com/colaboratory/faq.html).

## Models and actual use

SmolLM2-135M-Instruct (Apache-2.0) and Qwen3.5-0.8B (Apache-2.0) were downloaded as pinned GGUFs. `garden-agents/models.lock.json` records origin, quantizer, revision and SHA-256. SmolLM2 runs quickly on CPU, but complex role prompts produced repetition and incomplete analysis; it is a poor verifier. Qwen's 0.8B official card explicitly positions the scale for prototyping and task-specific research. SmolLM3-3B and larger Qwen3.5 variants are sensible next CPU/GPU candidates, but no unexecuted candidate is reported as an actual agent or stronger measured model.

Actual observations: SmolLM2 generated a useful calculator explanation with llama.cpp, and Qwen3.5-0.8B answered `12 + 30 = 42`. These native observations had no execution authority and are explicitly not sandbox receipts. The same official SmolLM2 weights exported to ONNX were then run with an explicit WASM provider through four advisory roles; outputs and elapsed times are recorded under `docs/observations`. A separate three-operation probe observed denied outside-file reads, writes and child-process launch. These finite probes do not prove absence of every bypass, and model correctness/independence remains UNKNOWN.

Sources: [SmolLM2 official card](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct), [Qwen3.5 official card](https://huggingface.co/Qwen/Qwen3.5-0.8B), [SmolLM3 official card](https://huggingface.co/HuggingFaceTB/SmolLM3-3B). Families help diversify correlated cognition; family diversity alone does not establish independence from common controllers, evidence or representations.

## Mature components and findings

| Component/research | Relevant lesson | Adoption |
|---|---|---|
| llama.cpp, MIT | CPU inference without a large Python tensor stack; weight formats and runtime versions must be pinned | Built at `a8c9a4e7ccba890d6a2644a235492f836a7371c3`; `llama-completion` target. |
| smolagents, Apache-2.0 | Useful model/tool adapters and sandbox options; code-agent execution must still traverse a Garden boundary | Investigated, not a gate dependency; omitted from the smallest trusted base. |
| gVisor, Apache-2.0 | A userspace kernel reduces host syscall exposure, but network/file mappings remain explicit administrator decisions | Deployment option; not installed or claimed active here. |
| Cedar policy language | Typed validation and default-deny authorization can be formally studied; policy correctness remains the operator's responsibility | Comparison/possible generic authorization backend; Garden evidence/QSE/human-effect semantics remain additional obligations. |
| AI Control (Greenblatt et al., ICML 2024) | Evaluate useful work and safety against intentionally subverting models, not only cooperative instructions | Motivates separate gate, distrust of proposer/monitor and adversarial tests. |
| SHADE-Arena / Anthropic sabotage work | A model may sabotage research or evade a weaker monitor; a monitor's approval is not ground truth | Motivates overlapping lineage records, material-omission tests and avoiding model self-certification. |

Primary sources: [llama.cpp](https://github.com/ggml-org/llama.cpp), [smolagents](https://github.com/huggingface/smolagents), [gVisor security model](https://gvisor.dev/docs/architecture_guide/security/), [Cedar authorization](https://docs.cedarpolicy.com/auth/authorization.html), [Cedar security](https://docs.cedarpolicy.com/other/security.html), [AI Control paper](https://proceedings.mlr.press/v235/greenblatt24a.html), [SHADE-Arena](https://www.anthropic.com/research/shade-arena-sabotage-monitoring), [research sabotage](https://alignment.anthropic.com/2025/automated-researchers-sandbag/).

Hash chains authenticate log continuity only when keys/checkpoints are protected. Hashes do not prove evidence truth or global completeness. Process identity changes do not by themselves provide a sandbox. Kernel/gate proofs cannot establish the completeness of human-effect classification or substantive independence of an entire model ecosystem.

## Dependency/license inventory

The agent/language implementation uses Python standard library only. The tested optional inference route uses llama.cpp/ggml and cpp-httplib (MIT), Apache-2.0 model weights, system OpenSSL (Apache-2.0), and ordinary host C/C++/OpenMP runtime libraries under their respective distribution licenses. Build-only helpers installed were CMake (BSD-3-Clause) and Ninja (Apache-2.0). No third-party framework governs Garden policy. Keep upstream copyright/license notices when redistributing binaries, weight conversions or container layers; model weights are fetched outside the source repository.

The fixed WASM runner additionally uses ONNXRuntime Web (MIT) and Tokenizers.js (Apache-2.0), pinned with an npm lockfile. Transformers.js was investigated but is not a production worker dependency: its Node adapter would ordinarily choose native ONNX, and simply labelling an adapter `wasm` is insufficient evidence of isolation. [ONNXRuntime Web](https://onnxruntime.ai/docs/tutorials/web/) documents WASM support; [Node permission documentation](https://nodejs.org/api/permissions.html) explicitly excludes malicious-code security guarantees. The JS loader/runtime remain trusted computing base, not a model's authority source.
