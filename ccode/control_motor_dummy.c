#include <stdio.h>
#include <stdlib.h>

int LED_PIN[] = {12, 13, 14, 11, 10};
void setup()
{
	printf("setup wiringPi");
}
void control_motor(int command)
{

	if (command > 4)
	{
		printf("Error : command must be specified from 0 to 4.\n");
		return;
	}

	printf("command:%d\n", command);

	return;
}
