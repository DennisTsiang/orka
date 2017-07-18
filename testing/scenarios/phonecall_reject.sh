#!/usr/bin/expect

lassign $argv PORT AUTH_TOKEN CALL_AFTER RING_FOR

# expect script that simulate a phone call reject via telnet

spawn telnet localhost $PORT
expect "OK"
send "auth $AUTH_TOKEN\n"
expect "OK"
sleep $CALL_AFTER
send "gsm call 0123456789\n"
expect "OK"
sleep $RING_FOR
send "gsm cancel 0123456789\n"
expect "OK"
