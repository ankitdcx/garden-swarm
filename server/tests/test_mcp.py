import asyncio

from mcp import Client

from server.mcp_service import mcp


def test_mcp_read_only_tools_are_available():
    async def run():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {
                'current_release',
                'list_attack_surfaces',
                'evaluation_instructions',
                'public_tasks',
                'build_finding_payload',
            }.issubset(names)

            result = await client.call_tool('current_release', {})
            assert result.is_error is False
            assert result.structured_content is not None
            assert result.structured_content['project'] == 'Garden'
            assert result.structured_content['status']['machine_certification'] == 'PENDING'

            attack = await client.call_tool('list_attack_surfaces', {})
            assert attack.is_error is False
            assert 'Attack Surface' in attack.content[0].text

    asyncio.run(run())


def test_mcp_finding_builder_is_payload_only():
    async def run():
        async with Client(mcp) as client:
            result = await client.call_tool(
                'build_finding_payload',
                {
                    'claim': 'Example claim',
                    'evidence_or_failure': 'Example counterexample',
                    'severity': 'LOW',
                    'test': 'Reproduce the example',
                },
            )
            assert result.is_error is False
            assert result.structured_content is not None
            assert 'No GitHub write' in result.structured_content['note']

    asyncio.run(run())
