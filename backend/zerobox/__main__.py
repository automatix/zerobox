"""Entry point for `python -m zerobox`."""

import uvicorn


def main() -> None:
    uvicorn.run("zerobox.app:create_app", factory=True, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
