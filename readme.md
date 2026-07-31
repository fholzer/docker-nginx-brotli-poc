# What is this?

This project is based on Alpine Linux, the official nginx image and an nginx module that provides static and dynamic brotli compression. [Brotli](https://github.com/google/brotli) and the [nginx brotli module](https://github.com/google/ngx_brotli) is software by Google.

# How to use this image

As this project is based on the official [nginx image](https://hub.docker.com/_/nginx/) look for instructions there. In addition to the standard configuration directives, you'll be able to use the brotli module specific ones, see [here for official documentation](https://github.com/google/ngx_brotli#configuration-directives)

# Releases

## Available Tags

* `latest` will always track the latest stable release
* `mainline` will always track the latest mainline release
* `v<x.y.z>` will track a specific version
* `v<x.y>` will track a specific minor version

If you want to always use the most recent version possible, use the `mainline` tag.

**Note that tags are not immutable!** If you want to be sure you're using a specific version, and keep it 100% unchanged, pin to the [image digest](https://docs.docker.com/dhi/explore/security-concepts/digests/). You can find the digest on the Docker Hub page for each tag.

## New Versions

Newly released Nginx versions are usually added to this repository within 7 days of release. Critical security issues are usually added faster. Please consider that this is a personal project, so I might not be able to keep up with the pace of releases. Recent changes to the build and release process should make it easier to add new versions faster going forward.

## Security

Each tag is rebuilt weekly, and whenever a new Nginx version is released and added to this repository.

In addition to always using the latest Alpine 3 base image, packages are updated to the latest available version during build.

## Version Deprecation

Currently I am planning to keep tags for the latest 2 minor versions for each release branch of nginx, stable and mainline.

Untagged images will be removed 12 months after the most recent pull, or after 24 months regardless of pulls.
