Running Undercrawler with Arachnado and Docker
==============================================

Currently, you need base "arachando" image built from
https://github.com/TeamHG-Memex/arachnado.

Next, build undercrawler-arachnado image:

    docker build -t undercrawler-arachnado ..

After that start everything with:

    docker-compose up

Arachnado UI will be exposed at port 8888, and Autologin UI as 8088.

In order to start the crawler, enter the url
into the main "website URL" input in the Arachnado UI. If you want to tweak
any settings (described in the top-level README),
press a cog icon to the right of the url input.
