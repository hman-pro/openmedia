# Build-only, never shipped in the runtime. APT verifies every index/package signature.
FROM python:3.13.15-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e
RUN apt-get update -o APT::Update::Error-Mode=any \
 && apt-get install --yes --no-install-recommends dpkg-dev=1.21.23 xz-utils=5.4.1-1+deb12u2 bzip2=1.0.8-5+b1 patch=2.7.6-7 \
 && dpkg-query -W > /collector-dpkg.tsv
