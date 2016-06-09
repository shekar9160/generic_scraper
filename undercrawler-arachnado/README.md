Running undercrawler with arachnado and docker
==============================================

Currently, you need base "arachando" image built from
https://github.com/TeamHG-Memex/arachnado.

Next, build undercrawler-arachnado image:

    docker build -t undercrawler-arachnado ..

After that start everything with:

    docker-compose up

Arachnado UI will be exposed at port 8888, and Autologin UI as 8088.