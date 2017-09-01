#!/usr/bin/expect

lassign $argv PORT AUTH_TOKEN SEND_AFTER
if {$SEND_AFTER eq ""} {set SEND_AFTER "0"}

# expect script that simulate a text message reception via telnet

spawn telnet localhost $PORT
expect "OK"
send "auth $AUTH_TOKEN\n"
expect "OK"
sleep $SEND_AFTER
send "sms send 0123456789 hello\n"
expect "OK"
