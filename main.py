from src.handlers.video_handler import BaseHandler

def main():
    import sys

    command = sys.argv[1] if len(sys.argv) > 1 else None

    handler = BaseHandler()
    handler.execute(command)


if __name__ == "__main__":
    main()
