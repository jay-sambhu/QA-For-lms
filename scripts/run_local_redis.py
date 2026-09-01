import sys
import fakeredis

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6379
    print(f"Starting local Redis TCP server on port {port}...")
    server = fakeredis.TcpFakeServer(("127.0.0.1", port))
    server.serve_forever()

if __name__ == "__main__":
    main()
