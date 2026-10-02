#!/usr/bin/env python3
"""Bounded transport to one fixed internal Garden endpoint.

This has no URL routing, CONNECT, policy, tool, shell or credential API. It only
relays bytes to the immutable gate-console:8080 target in the Compose network.
The gate still owns authentication, authority, execution and receipts.
"""
import asyncio

TARGET_HOST = 'gate-console'
TARGET_PORT = 8080
MAX_CONNECTIONS = 16
MAX_BYTES = 2 * 1024 * 1024
MAX_BUFFER = 65536
MAX_SECONDS = 30

class FixedTargetIngress:
    def __init__(self, *, timeout=MAX_SECONDS):
        self.timeout=timeout
        self.active=0

    async def _connect(self):
        return await asyncio.open_connection(TARGET_HOST,TARGET_PORT,limit=MAX_BUFFER)

    async def _close(self, *streams):
        for stream in streams:
            stream.close()
        try:
            async with asyncio.timeout(1):
                await asyncio.gather(*(s.wait_closed() for s in streams),return_exceptions=True)
        except TimeoutError:
            pass

    async def handle(self, reader, writer):
        if self.active>=MAX_CONNECTIONS:
            await self._close(writer)
            return
        self.active+=1
        upstream=None
        tasks=[]
        try:
            async with asyncio.timeout(self.timeout):
                upstream_reader,upstream=await self._connect()
                async def transfer(source,destination):
                    total=0
                    while True:
                        data=await source.read(MAX_BUFFER)
                        if not data:
                            if destination.can_write_eof():
                                destination.write_eof()
                                await destination.drain()
                            return
                        total+=len(data)
                        if total>MAX_BYTES:
                            raise ValueError('Transport byte limit')
                        destination.write(data)
                        await destination.drain()
                tasks=[asyncio.create_task(transfer(reader,upstream)),
                       asyncio.create_task(transfer(upstream_reader,writer))]
                done,pending=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
                for completed in done:
                    completed.result()
                # Client half-close ends its request, not the gate's response.
                # A completed gate response closes both streams immediately.
                if tasks[0] in done and tasks[1] not in done:
                    await tasks[1]
        except (OSError,TimeoutError,ValueError,asyncio.IncompleteReadError):
            # No payload or bearer credential is logged by this transport.
            pass
        finally:
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks,return_exceptions=True)
            try:
                await self._close(*([writer,upstream] if upstream else [writer]))
            finally:
                self.active-=1

async def main():
    relay=FixedTargetIngress()
    server=await asyncio.start_server(relay.handle,'0.0.0.0',8080,limit=MAX_BUFFER)
    async with server:
        await server.serve_forever()

if __name__=='__main__':
    asyncio.run(main())
