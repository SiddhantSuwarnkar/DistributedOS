/*
 * deadlock.c  –  Deadlock Detection Algorithm
 *
 * Function: detect_deadlock()
 *   Uses the resource-allocation graph / reduction algorithm to detect
 *   which processes are deadlocked.
 *
 * Parameters:
 *   p        – number of processes
 *   r        – number of resource types
 *   avail[]  – available resources vector (length r)
 *   alloc[]  – flattened allocation matrix [p][r], row-major
 *   req[]    – flattened request  matrix [p][r], row-major
 *              (blocked processes carry their pending need; running processes 0)
 *   dead[]   – output array filled with indices of deadlocked processes
 *
 * Returns:
 *   Number of deadlocked processes (0 means no deadlock)
 */

#ifndef DEADLOCK_C
#define DEADLOCK_C

int detect_deadlock(int p, int r,
                    int avail[],
                    int alloc[], int req[],
                    int dead[])
{
    int work[10];
    int finish[10];
    int dead_count = 0;

    /* work = available */
    for(int j = 0; j < r; j++)
        work[j] = avail[j];

    /* A process with no allocation is considered already finished */
    for(int i = 0; i < p; i++)
    {
        int empty = 1;
        for(int j = 0; j < r; j++)
        {
            if(alloc[i * r + j] != 0)
            {
                empty = 0;
                break;
            }
        }
        finish[i] = empty ? 1 : 0;
    }

    /* Reduction loop */
    while(1)
    {
        int found = 0;

        for(int i = 0; i < p; i++)
        {
            if(finish[i] == 0)
            {
                int possible = 1;

                for(int j = 0; j < r; j++)
                {
                    if(req[i * r + j] > work[j])
                    {
                        possible = 0;
                        break;
                    }
                }

                if(possible)
                {
                    for(int j = 0; j < r; j++)
                        work[j] += alloc[i * r + j];

                    finish[i] = 1;
                    found = 1;
                }
            }
        }

        if(found == 0)
            break;
    }

    /* Collect unfinished processes – these are deadlocked */
    for(int i = 0; i < p; i++)
    {
        if(finish[i] == 0)
            dead[dead_count++] = i;
    }

    return dead_count;
}

#endif /* DEADLOCK_C */