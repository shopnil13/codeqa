"""Module docstring."""
import os


class Client:
    """A simple client."""

    def send(self, request, *, stream=False):
        """Send a request."""
        return os.path.join(request, "x")

    async def aclose(self):
        pass


@staticmethod
def helper(x):
    return x + 1
