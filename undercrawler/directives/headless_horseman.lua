function get_arg(arg, default)
  if arg ~= nil then
    return arg
  else
    return default
  end
end

function main(splash)
  --[[
  The main Headless Horseman directive. It automatically tries every
  trick in the book, looking for elements that trigger XHR on click,
  n scroll, on mouseover, etc.
  ]]

  local debug = get_arg(splash.args.debug, false)
  local run_hh = get_arg(splash.args.run_hh, true)
  local return_har = get_arg(splash.args.return_har, true)
  local return_html = get_arg(splash.args.return_html, true)
  local return_png = get_arg(splash.args.return_png, true)
  local url = splash.args.url
  local http_method = get_arg(splash.args.http_method, "GET")
  local body = get_arg(splash.args.body, nil)
  local headers = get_arg(splash.args.headers, nil)
  local cookies = get_arg(splash.args.cookies, nil)
  local visual = get_arg(splash.args.visual, false)

  -- 992px is Bootstrap's minimum "desktop" size. 744 gives the viewport
  -- a nice 4:3 aspect ratio. We may need to tweak the viewport size even
  -- higher, based on real world usage...
  local viewport_width = splash.args.viewport_width or 992
  local viewport_height = splash.args.viewport_height or 744

  splash.images_enabled = get_arg(splash.args.images_enabled, true)
  -- Set different timeouts for the first and for other requests
  splash.resource_timeout = splash.args.resource_timeout or 15
  local first_request = true
  splash:on_request(function(request)
      if first_request then
          request:set_timeout(splash.args.first_request_timeout or 60)
          first_request = false
      end
  end)

  if cookies then
    splash:init_cookies(cookies)
  end
  splash:autoload(splash.args.js_source)

  if debug then
    splash:autoload("__headless_horseman__.setDebug(true);")
  end

  if visual then
    splash:autoload("__headless_horseman__.setVisual(true);")
  end

  splash:autoload("__headless_horseman__.patchAll();")
  splash:set_viewport_size(viewport_width, viewport_height)
  local ok, reason = splash:go{
    url, http_method=http_method, headers=headers, body=body }
  if #(splash:history()) == 0 then
    assert(false, reason)
  end
  splash:lock_navigation()

  -- Run a battery of Headless Horseman tests.

  if run_hh then
    splash:wait_for_resume([[
      function main(splash) {
        __headless_horseman__
          .wait(3000)
          .then(__headless_horseman__.tryInfiniteScroll, 3)
          .then(__headless_horseman__.tryClickXhr, 3)
          .then(__headless_horseman__.tryMouseoverXhr, 3)
          .then(__headless_horseman__.scroll, window, 'left', 'top')
          .then(__headless_horseman__.cleanup)
       // .then(__headless_horseman__.removeOverlays)
          .then(splash.resume);
      }
    ]])

    splash:stop()
    splash:set_viewport_full()
    splash:wait(1)
  end

  -- Render and return the requested outputs.

  local render = {}
  local entries = splash:history()
  local last_entry = entries[#entries]

  if return_har then
    render['har'] = splash:har{reset=true}
  end

  if return_html then
    render['html'] = splash:html()
  end

  if return_png then
    render['png'] = splash:png{width=viewport_width}
  end

  render['url'] = splash:url()
  render['cookies'] = splash:get_cookies()

  if last_entry then
    local last_response = entries[#entries].response
    render['headers'] = last_response.headers
    render['http_status'] = last_response.status
  end

  return render
end
