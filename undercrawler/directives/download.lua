function main(splash)

  local cookies = splash.args.cookies
  if cookies then
    splash:init_cookies(cookies)
  end

  response = splash:http_get{splash.args.url, headers=splash.args.headers}
  if response.ok then
    return response.body
  else
    return {
      ok = response.ok,
      body = response.body,
      http_status = response.status,
      headers = response.headers,
    }
  end
end
