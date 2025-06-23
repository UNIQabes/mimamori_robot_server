ccode/control_motor.so : ccode/control_motor_dummy.c
	gcc -shared -o $@ $^ 

run_robot : ccode/control_motor.so 
	./server.py




