function scroll_to(splash, x, y)
  local js = string.format(
    "window.scrollTo(%s, %s);",
    tonumber(x),
    tonumber(y)
  )
  return splash:runjs(js)
end


function scroll_to_inf(splash)
  return splash:runjs([[
    window.scrollTo(0, 1000000)
  ]])
end


function get_doc_height(splash)
  return splash:runjs([[
    document.body.scrollHeight
  ]])
end


function get_max_doc_height(splash)
  return splash:runjs([[
    Math.max(
        document.body.scrollHeight,
        document.body.offsetHeight,
        document.body.clientHeight
    )
  ]])
end


function scroll_to_bottom(splash)
  local y = get_max_doc_height(splash)
  return scroll_to(splash, 0, y)
end


function wait_until_height_increases(splash, old_height)
  for j=1,5 do
    new_height = get_doc_height(splash)
    if new_height > old_height then
      break
    end
    assert(splash:wait(0.5))
  end
end


function main(splash)

  -- e.g. http://infiniteajaxscroll.com/examples/basic/page1.html
  local url = splash.args.url
  local page_count = splash.args.page_count or 2
  assert(splash:go(url))

  for i=1,page_count do
    local old_height = get_doc_height(splash)
    scroll_to_bottom(splash)
    wait_until_height_increases(splash, old_height)
  end

  splash:stop()
  splash:set_viewport("full")

  return {
    html = splash:html(),
    png = splash:png{width=640},
    har = splash:har(),
  }
end
