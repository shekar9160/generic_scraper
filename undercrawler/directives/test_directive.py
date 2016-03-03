import argparse
import base64
import codecs
import json
import os
import sys

import requests


LUA_SCRIPT = './headless_horseman.lua'
JS_SCRIPT = './headless_horseman.js'


def get_args():
    ''' Parse command line arguments. '''

    parser = argparse.ArgumentParser(
        description='Run the Headless Horseman directive on a single target.'
    )

    parser.add_argument(
        '--debug',
        dest='debug',
        action='store_true',
        help='Enable the directive\'s verbose JavaScript logging.'
    )

    parser.add_argument(
        '--no-debug',
        dest='debug',
        action='store_false',
        help='Disable debug mode. (Default)'
    )

    parser.add_argument(
        '--har-out',
        metavar='PATH',
        help='Path to write HAR data to. If not specified, no HAR data is saved.'
    )

    parser.add_argument(
        '--html-out',
        metavar='PATH',
        help='Path to write HTML source to. If not specified, no HTML is saved.'
    )

    parser.add_argument(
        '--png-out',
        metavar='PATH',
        help='Path to write PNG screenshot to. If not specified, no PNG is saved.'
    )

    parser.add_argument(
        '--splash-url',
        metavar='SPLASH',
        default='http://localhost:8050/execute',
        help='URL for Splash. Defaults to http://localhost:8050/execute.'
    )

    parser.add_argument(
        'target_url',
        help='The URL to process with Headless Horseman.'
    )

    parser.add_argument(
        '--timeout',
        type=float,
        default=30,
        help='The HTTP timeout (seconds) before giving up on a Splash' \
             ' request. (Default: 30).'
    )

    parser.add_argument(
        '--viewport',
        default='992x744',
        metavar='WIDTHxHEIGHT',
        help='Browser\'s viewport size. (Default: "992x744")'
    )

    parser.add_argument(
        '--visual',
        dest='visual',
        action='store_true',
        help='Enable visual mode: useful for visual demonstration.'
    )

    parser.add_argument(
        '--no-visual',
        dest='visual',
        action='store_false',
        help='Disable visual mode. (Default)'
    )

    parser.set_defaults(debug=False, visual=False)

    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()

    if not args.har_out and not args.html_out and not args.png_out:
        print('You should specify at least one of  --har-out, --html-out,' \
              ' or --png-out.')
        sys.exit(1)

    try:
        viewport_width, viewport_height = map(int, args.viewport.split('x'))
    except:
        print('Viewport size is invalid. It should look like this: "1024x768".')
        sys.exit(1)

    lua_path = os.path.join(os.path.dirname(__file__), LUA_SCRIPT)
    js_path = os.path.join(os.path.dirname(__file__), JS_SCRIPT)

    try:
        lua_file = open(lua_path, 'r')
        lua_script = lua_file.read()
    except:
        print('Unable to find Headless Horseman Lua script. Expected to'
              ' find it at: %s', lua_path)
    finally:
        if lua_file is not None:
            lua_file.close()

    try:
        js_file = open(js_path, 'r')
        js_script = js_file.read()
    except:
        print('Unable to find Headless Horseman JavaScript script. Expected to'
              ' find it at: %s', js_path)
    finally:
        js_file.close()

    data = json.dumps({
        'debug': args.debug,
        'lua_source': lua_script,
        'js_source': js_script,
        'return_har': bool(args.har_out),
        'return_html': bool(args.html_out),
        'return_png': bool(args.png_out),
        'url': args.target_url,
        'viewport_height': viewport_height,
        'viewport_width': viewport_width,
        'visual': args.visual,
    })

    print("Requesting %s" % args.target_url)
    splash_headers = {'content-type':'application/json'}

    response = requests.post(
        args.splash_url,
        data=data,
        headers=splash_headers,
        timeout=args.timeout
    )

    if response.status_code == 200:
        print("Received response.")
        payload = json.loads(response.text)

        if args.har_out:
            with open(args.har_out, 'wb') as har:
                har.write(json.dumps(payload['har']))
            print("Wrote HAR to: %s" % args.har_out)

        if args.html_out:
            encoding = response.encoding or 'utf-8'
            with open(args.html_out, 'wb') as html:
                html.write(payload['html'].encode(encoding))
            print("Wrote HTML to: %s" % args.html_out)

        if args.png_out:
            with open(args.png_out, 'wb') as png:
                png.write(base64.b64decode(payload['png']))
            print("Wrote PNG to: %s" % args.png_out)

        print("Done.")
    else:
        print("ERROR: %d\n%s" % (response.status_code, response.text))
