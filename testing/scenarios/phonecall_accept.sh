#!/usr/bin/expect

lassign $argv PORT AUTH_TOKEN CALL_AFTER RING_FOR CALL_TIME

# expect script that simulate a phone call accept via telnet

spawn telnet localhost $PORT
expect "OK"
send "auth $AUTH_TOKEN\n"
expect "OK"
sleep $CALL_AFTER
send "gsm call 0123456789\n"
expect "OK"
sleep $RING_FOR
send "gsm accept 0123456789\n"
expect "OK"
sleep $CALL_TIME
send "gsm cancel 0123456789\n"
expect "OK"
