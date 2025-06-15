#include<stdio.h>
#include<stdlib.h>
#include<wiringPi.h>

int LED_PIN[]={12,13,14,11,10};
void setup(){
	if(wiringPiSetup()==-1){
                printf("Error : setup failed. \n");
                return;
        }
}
void control_motor (int command){
	
	if(command > 4){
		printf("Error : command must be specified from 0 to 4.\n");
		return;
	}
	
	
	for(int i =0;i<5;i++){
		int onoff=0;
		if(i==command){
			onoff=1;
		}
		pinMode(LED_PIN[i],OUTPUT);
        	digitalWrite(LED_PIN[i],onoff);
		printf("command:%d\n",command);
	}
	return;
}
