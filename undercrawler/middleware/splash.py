import scrapy_splash.middleware


class SplashMiddleware(scrapy_splash.middleware.SplashMiddleware):
    def process_request(self, request, spider):
        response = super().process_request(request, spider)
        if response is not None:
            # Raise priority of rescheduled request, so it spends less time
            # waiting in the queue after it has been prepared.
            response.priority += 100
        return response
