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
  local return_har = get_arg(splash.args.return_har, true)
  local return_html = get_arg(splash.args.return_html, true)
  local return_png = get_arg(splash.args.return_png, true)
  local url = splash.args.url
  local visual = get_arg(splash.args.visual, false)

  -- 992px is Bootstrap's minimum "desktop" size. 744 gives the viewport
  -- a nice 4:3 aspect ratio. We may need to tweak the viewport size even
  -- higher, based on real world usage...
  local viewport_width = splash.args.viewport_width or 992
  local viewport_height = splash.args.viewport_height or 744

  splash:autoload(splash.args.js_source)

  if debug then
    splash:autoload("__headless_horseman__.setDebug(true);")
  end

  if visual then
    splash:autoload("__headless_horseman__.setVisual(true);")
  end

  splash:autoload("__headless_horseman__.patchAll();")
  splash:set_viewport_size(viewport_width, viewport_height)
  assert(splash:go(url))
  splash:lock_navigation()

  -- Run a battery of Headless Horseman tests.

  splash:wait_for_resume([[
    function main(splash) {
      __headless_horseman__
        .wait(3000)
        .then(__headless_horseman__.tryInfiniteScroll, 3)
        .then(__headless_horseman__.tryClickXhr, 3)
        .then(__headless_horseman__.tryMouseoverXhr, 3)
        .then(__headless_horseman__.scroll, window, 'left', 'top')
        .then(__headless_horseman__.cleanup)
        .then(__headless_horseman__.removeOverlays)
        .then(splash.resume);
    }
  ]])

  splash:stop()
  splash:set_viewport_full()
  splash:wait(1)

  -- Render and return the requested outputs.

  render = {}

  if return_har then
    render['har'] = splash:har()
  end

  if return_html then
    render['html'] = splash:html()
  end

  if return_png then
    render['png'] = splash:png{width=viewport_width}
  end

  return render
end
