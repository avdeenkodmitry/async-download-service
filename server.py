from aiohttp import web
import asyncio
import aiofiles
import os
import logging

INTERVAL_SECS = 1
DEBUG = False
SLEEP_TIMEOUT = 1


async def archivate(request):
    log_format = u'%(filename)s[LINE:%(lineno)d]# ' \
                 u'%(levelname)s [%(asctime)s]  %(message)s'
    logging.basicConfig(format=log_format, level=logging.DEBUG)

    archive_hash = request.match_info.get('archive_hash')
    path = 'test_photos/{}'.format(archive_hash)

    if os.path.isdir(path):
        response = web.StreamResponse()
        proc = await asyncio.create_subprocess_exec(
            *["zip", "-r", "-", path],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        response.headers['Content-Type'] = 'form-data'
        content_disposition = 'attachment;filename="photos.zip"'
        response.headers['Content-Disposition'] = content_disposition

        await response.prepare(request)
        try:
            while True:
                logging.info("Sending archive chunk ...")
                archive = await proc.stdout.read(100 * 1024)

                if DEBUG:
                    await asyncio.sleep(SLEEP_TIMEOUT)

                with open("photos.zip", "ab") as f:
                    await response.write(bytearray(archive))

                if not archive:
                    break
        except asyncio.CancelledError:
            try:
                outs, errs = await asyncio.wait_for(proc.communicate(),
                                                    timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                outs, errs = await proc.communicate()
            raise
        finally:
            logging.info("Download was interrupted")
    else:
        response = web.StreamResponse(status=404)
        response.headers['Content-Type'] = 'text/html'
        message = f'Archive not exist or was deleted<br>'
        await response.prepare(request)
        await response.write(message.encode('utf-8'))
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
