#!/usr/bin/env python3
"""Real loopback sockets; production target is never selected from user input."""
import asyncio
import unittest
from ingress import FixedTargetIngress,MAX_CONNECTIONS,MAX_BYTES

class IngressTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.servers=[]
    async def asyncTearDown(self):
        for server in self.servers:
            server.close()
            await server.wait_closed()
    async def bind(self,handler):
        server=await asyncio.start_server(handler,'127.0.0.1',0)
        self.servers.append(server)
        return server.sockets[0].getsockname()[1]
    async def relay(self,upstream,timeout=.25):
        gate_port=await self.bind(upstream)
        # Test subclass fixes a real socket target; production has no such input.
        class LocalRelay(FixedTargetIngress):
            async def _connect(self):
                return await asyncio.open_connection('127.0.0.1',gate_port)
        relay=LocalRelay(timeout=timeout)
        return relay,await self.bind(relay.handle)
    async def test_real_request_and_response_bytes(self):
        observed=[]
        async def upstream(reader,writer):
            observed.append(await reader.readexactly(4))
            writer.write(b'HTTP/1.0 200 OK\r\n\r\n391')
            await writer.drain()
            writer.close();await writer.wait_closed()
        relay,port=await self.relay(upstream)
        reader,writer=await asyncio.open_connection('127.0.0.1',port)
        writer.write(b'PING');await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.read(),1),b'HTTP/1.0 200 OK\r\n\r\n391')
        writer.close();await writer.wait_closed()
        self.assertEqual(observed,[b'PING'])
        await asyncio.sleep(.01)
        self.assertEqual(relay.active,0)
    async def test_stalled_client_connection_is_closed(self):
        async def upstream(reader,writer):
            await reader.read()
            writer.close();await writer.wait_closed()
        relay,port=await self.relay(upstream,timeout=.05)
        reader,writer=await asyncio.open_connection('127.0.0.1',port)
        self.assertEqual(await asyncio.wait_for(reader.read(),.5),b'')
        writer.close();await writer.wait_closed()
        await asyncio.sleep(.01)
        self.assertEqual(relay.active,0)
    async def test_client_half_close_preserves_response(self):
        async def upstream(reader,writer):
            request=await reader.read()
            writer.write(b'ACK:'+request)
            await writer.drain()
            writer.close();await writer.wait_closed()
        relay,port=await self.relay(upstream)
        reader,writer=await asyncio.open_connection('127.0.0.1',port)
        writer.write(b'PING');await writer.drain();writer.write_eof()
        self.assertEqual(await asyncio.wait_for(reader.read(),1),b'ACK:PING')
        writer.close();await writer.wait_closed()
    async def test_transport_byte_budget_stops_oversized_stream(self):
        observed=[]
        complete=asyncio.Event()
        async def upstream(reader,writer):
            total=0
            while data:=await reader.read(65536):
                total+=len(data)
            observed.append(total)
            writer.close();await writer.wait_closed()
            complete.set()
        relay,port=await self.relay(upstream,timeout=1)
        reader,writer=await asyncio.open_connection('127.0.0.1',port)
        writer.write(b'x'*(MAX_BYTES+1));await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.read(),2),b'')
        await asyncio.wait_for(complete.wait(),1)
        self.assertLessEqual(observed[0],MAX_BYTES)
        writer.close();await writer.wait_closed()
    async def test_connection_limit_does_not_open_upstream(self):
        relay=FixedTargetIngress(timeout=.05);relay.active=MAX_CONNECTIONS
        port=await self.bind(relay.handle)
        reader,writer=await asyncio.open_connection('127.0.0.1',port)
        self.assertEqual(await asyncio.wait_for(reader.read(),.5),b'')
        writer.close();await writer.wait_closed()
        self.assertEqual(relay.active,MAX_CONNECTIONS)

if __name__=='__main__':
    unittest.main()
