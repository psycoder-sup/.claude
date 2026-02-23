#!/bin/sh
pagesize=$(sysctl -n hw.pagesize)
total=$(sysctl -n hw.memsize)
free=$(vm_stat | grep "Pages free" | awk -F: '{print int($2)}')
inactive=$(vm_stat | grep "Pages inactive" | awk -F: '{print int($2)}')
purgeable=$(vm_stat | grep "Pages purgeable" | awk -F: '{print int($2)}')
speculative=$(vm_stat | grep "Pages speculative" | awk -F: '{print int($2)}')
echo "$free $inactive $purgeable $speculative $pagesize $total" | awk '{avail=($1+$2+$3+$4)*$5; printf "%.0f%%", (1-avail/$6)*100}'
