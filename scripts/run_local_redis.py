#!/usr/bin/env python3
import time
import fakeredis

def main():
    print("Starting local Redis TCP server on 127.0.0.1:6379...")
    server = fakeredis.TcpFakeServer(("127.0.0.1", 6379))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Redis server...")
        server.shutdown()

if __name__ == "__main__":
    main()
