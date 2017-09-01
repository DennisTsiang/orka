#!/usr/bin/expect

# expect script that sets the charging status to off and the battery capacity
#   to $CAP via telnet

lassign $argv PORT AUTH_TOKEN CAP
if {$CAP eq ""} {set CAP "100"}

spawn telnet localhost $PORT
expect "OK"
send "auth $AUTH_TOKEN\n"
expect "OK"
send "power ac off\n"
expect "OK"
send "power capacity $CAP\n"
expect "OK"
