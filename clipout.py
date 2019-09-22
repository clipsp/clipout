#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Clipout - Process output manipulation tool.

    Clipboard Server Project
    Copyright (C) 2019  Sepalani

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import select
import socket
import sys
import threading

try:
    import Queue
except ImportError:
    import queue as Queue


def dumb_worker(f, q):
    input_data = f.read(1)
    while input_data:
        q.put(input_data)
        input_data = f.read(1)
    q.put(input_data)


def main(args):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((args.host, args.port))
    server_socket.listen(args.backlog)
    sys.stderr.write("[CLIPOUT] Listening on {}:{}\n".format(
        args.host, args.port
    ))

    q = Queue.Queue()
    if sys.version_info >= (3, 0):
        STDIN = sys.stdin.buffer
        STDOUT = sys.stdout.buffer
        STDERR = sys.stderr
    else:
        # Python 2 on Windows opens sys.stdin in text mode, and
        # binary data that read from it becomes corrupted on \r\n
        if sys.platform == "win32":
            import os
            import msvcrt
            msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        STDIN = sys.stdin
        STDOUT = sys.stdout
        STDERR = sys.stderr
    t = threading.Thread(target=dumb_worker, args=(STDIN, q))
    t.daemon = True
    t.start()

    input_list = [server_socket]
    output_list = []
    while input_list:
        rlist, wlist, xlist = select.select(input_list, output_list, [], 0)

        if server_socket in rlist:
            client_socket, client_address = server_socket.accept()
            STDERR.write("[CLIPOUT] Open client {}:{}\n".format(
                *client_address
            ))
            input_list.append(client_socket)
            output_list.append(client_socket)
            continue

        for client in rlist:
            client_data = client.recv(args.buffer_size)
            if client_data:
                q.put(client_data)
                continue
            STDERR.write("[CLIPOUT] Close client {}:{}\n".format(
                *client.getpeername()
            ))
            client.close()
            input_list.remove(client)
            output_list.remove(client)

        try:
            data = q.get_nowait()
            if not data:
                STDERR.write("[CLIPOUT] STDIN closed\n")
                input_list.remove(server_socket)
        except Queue.Empty:
            continue

        if not wlist:
            STDOUT.write(data)
            STDOUT.flush()
            continue
        for client in wlist:
            try:
                client.sendall(data)
            except IOError:
                continue

    STDERR.write("[CLIPOUT] No input left\n")


if __name__ == "__main__":
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "-a", "--host", type=str, default="127.0.0.1",
        help="Listener host address"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=21001,
        help="Listener port number"
    )
    parser.add_argument(
        "-l", "--backlog", type=int, default=5,
        help="Listener backlog size"
    )
    parser.add_argument(
        "-b", "--buffer-size", type=int, default=256,
        help="Listener buffer size"
    )
    try:
        main(parser.parse_args())
    except KeyboardInterrupt:
        sys.stderr.write("[CLIPOUT] Interrupted!\n")
    sys.stderr.write("[CLIPOUT] Closing...\n")
