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


if __name__ == "__main__":
    import socket
    import sys
    from select import select

    HOST = "127.0.0.1"
    PORT = 21001
    BUFFER_SIZE = 256

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    sys.stderr.write("[CLIPOUT] Listenning on {}:{}\n".format(HOST, PORT))

    input_list = [sys.stdin, server_socket]
    output_list = [sys.stdout]
    while True:
        rlist, wlist, xlist = select(input_list, output_list, [], 0.5)
        if not wlist:
            sys.stderr.write("[CLIPOUT] Can't write anymore\n")
            break
        for fd in rlist:
            if server_socket in rlist:
                # Handle new client
                client_socket, address = server_socket.accept()
                sys.stderr.write("[CLIPOUT] New client {}:{}\n".format(
                    *address
                ))
                input_list.append(client_socket)
                output_list.append(client_socket)
                break
            elif sys.stdin in rlist:
                # Handle process input
                data = sys.stdin.readline()
                if not data:
                    server_socket.close()
                    input_list.remove(sys.stdin)
                    input_list.remove(server_socket)
                    continue
                # Transfer them to clients or stdout
                for fd in wlist:
                    if fd == sys.stdout and len(wlist) == 1:
                        sys.stdout.write(data)
                        sys.stdout.flush()
                    elif fd != sys.stdout:
                        fd.sendall(data)
            else:
                # Handle client input
                data = fd.recv(BUFFER_SIZE)
                if not data:
                    fd.close()
                    input_list.remove(fd)
                    output_list.remove(fd)
                sys.stdout.write(data)
        if not input_list:
            sys.stderr.write("[CLIPOUT] Can't read anymore\n")
            break
