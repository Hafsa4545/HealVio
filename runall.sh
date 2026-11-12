#!/bin/bash
cd /home/claude/test/live
for t in t4b t8 t9_calls t10_ice t11_push t12_update t13_reason t15_ai t16_paypal t17_meds t18_delivery t19_orders t20_doctor t21_features t22_final t23_push t24_fixes t25_legal t26_notify t27_cache t28_views t29_tr_pay t30_avail t31_timer t32_lang t33_favs t34_notes; do
  out=$(timeout 400 python3 $t.py 2>&1); code=$?
  last=$(echo "$out" | grep -E "PASSED|FAILED|Error|Traceback" | tail -1)
  fails=$(echo "$out" | grep -E "^FAIL" | head -5)
  echo "== $t (exit $code): $last"; [ -n "$fails" ] && echo "$fails"
done
cd /home/claude/test
for t in wtest3 wtest4 wtest5 wtest6 wtest7 wtest8 wtest9 wtest10 wtest11 swtest swtest2 swtest3 swtest4; do
  f=$(ls $t.* 2>/dev/null | head -1); [ -z "$f" ] && { echo "== $t missing"; continue; }
  out=$(timeout 300 node $f 2>&1); code=$?
  echo "== $t (exit $code): $(echo "$out" | tail -1)"
  echo "$out" | grep -iE "^FAIL|✗" | head -5
done
echo ALLDONE
