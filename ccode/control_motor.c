#include <stdio.h>
#include <stdlib.h>
#include <wiringPi.h>

int LED_PIN[] = {12, 13, 14, 11, 10};
void setup()
{
	if (wiringPiSetup() == -1)
	{
		printf("Error : setup failed. \n");
		return;
	}
}
void control_motor(int command)
{

	if (command > 4)
	{
		printf("Error : command must be specified from 0 to 4.\n");
		return;
	}

	for (int i = 0; i < 5; i++)
	{
		int onoff = 0;
		if (i == command)
		{
			onoff = 1;
		}
		pinMode(LED_PIN[i], OUTPUT);
		digitalWrite(LED_PIN[i], onoff);
		printf("command:%d\n", command);
	}
	/*
	pinMode(0, OUTPUT);
	pinMode(1, OUTPUT);
	pinMode(2, OUTPUT);
	pinMode(4, OUTPUT);

	if (command == 1)
	{
		digitalWrite(0, 0);
		digitalWrite(1, 0);
		digitalWrite(2, 1);
		digitalWrite(4, 1);
	}

	if (command == 2)
	{
		digitalWrite(0, 1);
		digitalWrite(1, 1);
		digitalWrite(2, 0);
		digitalWrite(4, 0);
	}

	if (command == 3)
	{
		digitalWrite(0, 1);
		digitalWrite(1, 0);
		digitalWrite(2, 0);
		digitalWrite(4, 1);
	}

	if (command == 4)
	{
		digitalWrite(0, 0);
		digitalWrite(1, 1);
		digitalWrite(2, 1);
		digitalWrite(4, 0);
	}

	if (command == 0)
	{
		digitalWrite(0, 0);
		digitalWrite(1, 0);
		digitalWrite(2, 0);
		digitalWrite(4, 0);
	}
	*/

	/*
	if (command == 0)
	{
		digitalWrite(0, 1);
		digitalWrite(1, 1);
		digitalWrite(2, 1);
		digitalWrite(4, 1);
	}
	*/

	return;
}
