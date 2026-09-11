#!/bin/bash
echo "=== DIAGNOSTIC MODE ==="
echo "--- apps dir ---"
ls -la /home/frappe/frappe-bench/apps/ 2>&1
echo "--- sites/apps.txt (image build-time, before volume) ---"
cat /home/frappe/frappe-bench/sites/apps.txt 2>&1
echo "--- pip show payments (as frappe) ---"
su frappe -c "/home/frappe/frappe-bench/env/bin/pip show payments" 2>&1
echo "--- pip show lms (as frappe) ---"
su frappe -c "/home/frappe/frappe-bench/env/bin/pip show lms" 2>&1
echo "--- python import payments (as frappe, using bench's venv python) ---"
su frappe -c "/home/frappe/frappe-bench/env/bin/python -c 'import payments; print(payments.__file__)'" 2>&1
echo "--- site-packages easy-install / editable pointers ---"
su frappe -c "ls /home/frappe/frappe-bench/env/lib/python3.11/site-packages/ | grep -i 'payment\|lms\|__editable__'" 2>&1
echo "=== SLEEPING FOR INSPECTION ==="
sleep infinity
