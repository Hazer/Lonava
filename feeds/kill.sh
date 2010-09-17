#!/bin/bash
kill -9 `ps ux | awk '/reddit/ && !/awk/ {print $2}'`
kill -9 `ps ux | awk '/news/ && !/awk/ {print $2}'`
kill -9 `ps ux | awk '/generic/ && !/awk/ {print $2}'`

