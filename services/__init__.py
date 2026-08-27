"""Business logic that isn't tied to any one HTTP route.

Route handlers in routes/ stay thin: parse the request, call into here,
shape the response. Anything that touches SQL beyond a single lookup, or
that two different routes both need, belongs in this package instead of
being duplicated or buried inside a view function.
"""
