#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[])
{
    if(argc < 3)
    {
        printf("0");
        return 0;
    }

    char algo[20];
    strcpy(algo, argv[1]);

    int n = argc - 2;
    int burst[100];
    int priority[100];

    for(int i = 0; i < n; i++)
    {
        burst[i] = atoi(argv[i + 2]);

        /* demo priority derived from burst
           smaller number = higher priority */
        priority[i] = (burst[i] % 5) + 1;
    }

    if(strcmp(algo, "FCFS") == 0)
    {
        printf("0");
    }

    else if(strcmp(algo, "SJF") == 0)
    {
        int idx = 0;

        for(int i = 1; i < n; i++)
        {
            if(burst[i] < burst[idx])
                idx = i;
        }

        printf("%d", idx);
    }

    else if(strcmp(algo, "PRIORITY") == 0)
    {
        int idx = 0;

        for(int i = 1; i < n; i++)
        {
            if(priority[i] < priority[idx])
                idx = i;

            else if(priority[i] == priority[idx] &&
                    burst[i] < burst[idx])
                idx = i;
        }

        printf("%d", idx);
    }

    else if(strcmp(algo, "RR") == 0)
    {
        static int last = -1;

        last = (last + 1) % n;
        printf("%d", last);
    }

    else
    {
        printf("0");
    }

    return 0;
}