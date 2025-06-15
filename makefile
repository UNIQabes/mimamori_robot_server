ccode/control_motor.so : ccode/control_motor.c
	gcc -shared -o $@ $^ -lwiringPi

run_robot : ccode/control_motor.so 
	./server.py


