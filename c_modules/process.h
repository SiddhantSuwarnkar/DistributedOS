#ifndef PROCESS_H
#define PROCESS_H

#define MAX_RESOURCES 5

#define NEW 0
#define READY 1
#define RUNNING 2
#define WAITING 3
#define TERMINATED 4

typedef struct
{
    int pid;

    int arrival;
    int burst;
    int remaining;

    int memory;
    int disk;

    int priority;

    int max[MAX_RESOURCES];
    int allocation[MAX_RESOURCES];
    int need[MAX_RESOURCES];

    int state;

    int completion;
    int waiting;
    int turnaround;

    char command[100];

} Process;

#endif