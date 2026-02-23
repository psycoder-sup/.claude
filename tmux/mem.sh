#!/bin/sh
total=$(sysctl -n hw.memsize)
active=$(vm_stat | grep "Pages active" | awk -F: '{print int($2)}')
wired=$(vm_stat | grep "Pages wired" | awk -F: '{print int($2)}')
compressed=$(vm_stat | grep "Pages compressed" | awk -F: '{print int($2)}')
used=$(( (active + wired + compressed) * 4096 ))
echo "$used $total" | awk '{printf "%.0f%%", $1/$2*100}'
