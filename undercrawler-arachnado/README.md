Running Undercrawler with Arachnado and Docker
==============================================

Currently, you need base "arachando" image built from
https://github.com/TeamHG-Memex/arachnado.

Next, build undercrawler-arachnado image:

    docker build -t undercrawler-arachnado ..

After that start everything with:

    docker-compose up

Arachnado UI will be exposed at port 8888, and Autologin UI as 8088.

In order to start the crawler, enter ``spider://uc``
into the main "website URL" input in the Arachnado UI,
set target URL via ``url`` spider argument
(press a cog icon to the right of the url input to reveal arguments and settings),
and pass settings as required (see main README for useful settings to tweak).
