/*
 * bankers.c  –  Banker's Algorithm (Safety Check)
 *
 * Function: bankers_is_safe()
 *   Checks whether the system is in a safe state using the Banker's Algorithm.
 *
 * Parameters:
 *   p        – number of processes
 *   r        – number of resource types
 *   avail[]  – available resources vector (length r)
 *   max[]    – flattened max-demand matrix [p][r], row-major
 *   alloc[]  – flattened allocation matrix [p][r], row-major
 *
 * Returns:
 *   1 if a safe sequence exists (SAFE state)
 *   0 if no safe sequence exists (UNSAFE state)
 */

#ifndef BANKERS_C
#define BANKERS_C

#include <string.h>

int bankers_is_safe(int p, int r, int avail[], int max[], int alloc[])
{
    int work[10];
    int finish[10];
    int safe_seq[10];
    int need[10][10];
    int count = 0;

    /* Initialise work = available */
    for(int j = 0; j < r; j++)
        work[j] = avail[j];

    /* Initialise finish[] = 0 and compute need[][] */
    for(int i = 0; i < p; i++)
    {
        finish[i] = 0;
        for(int j = 0; j < r; j++)
            need[i][j] = max[i * r + j] - alloc[i * r + j];
    }

    /* Find a safe sequence */
    while(count < p)
    {
        int found = 0;

        for(int i = 0; i < p; i++)
        {
            if(finish[i] == 0)
            {
                int possible = 1;

                for(int j = 0; j < r; j++)
                {
                    if(need[i][j] > work[j])
                    {
                        possible = 0;
                        break;
                    }
                }

                if(possible)
                {
                    for(int j = 0; j < r; j++)
                        work[j] += alloc[i * r + j];

                    safe_seq[count++] = i;
                    finish[i] = 1;
                    found = 1;
                }
            }
        }

        if(found == 0)
            return 0; /* UNSAFE */
    }

    return 1; /* SAFE */
}

#endif /* BANKERS_C */