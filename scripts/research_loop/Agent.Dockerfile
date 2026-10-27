FROM golang@sha256:e47f121850f4e276b2b210c56df3fda9191278dd84a3a442bfe0b09934462a8f
RUN apk add --no-cache bash git python3 && ln -s /usr/bin/python3 /usr/local/bin/python
ENV CGO_ENABLED=0 GOPROXY=off GOTOOLCHAIN=local PAGER=cat
WORKDIR /work
