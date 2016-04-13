function main(splash)

  local cookies = splash.args.cookies
  if cookies then
    splash:init_cookies(cookies)
  end

  response = splash:http_get{splash.args.url, headers=splash.args.headers}
  assert(response.ok) -- TODO?

  return response.body
end
