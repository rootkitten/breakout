# Breakout

[![Build Status][1]][2]

Breakout is a tiny implementation of the circuit breaker microservice pattern
for asynchronous frameworks. It was built with extensibility and flexibility in mind,
and it can be easily integrated with any asynchronous framework of your choice.

If you have never heard of the circuit breaker pattern, you can read about it in
[this][3] excellent article.

## Building

Although Breakout itself does not depend on any particular Python third-party module,
you might want to install its development dependencies to be able to run the provided
examples and test suites.

Breakout uses [Poetry][4] package manager to manage its development dependencies. As
long as you have Poetry installed on your system, seting up the development environment
should be as easy as cloning this repository and running:

```
poetry install
```

This should get you ready for the next steps.

## Examples

Breakout comes with a simple example that demonstrates its core capabilities. To run
it, make sure you have built the development environment and run the following command:

```
poetry run python example.py
```

If you now visit `localhost:8888` using your favorite browser, you should be able to
play with the example application.

[1]: https://travis-ci.org/rootkitten/breakout.svg?branch=master
[2]: https://travis-ci.org/rootkitten/breakout
[3]: https://martinfowler.com/bliki/CircuitBreaker.html
[4]: https://github.com/sdispater/poetry
