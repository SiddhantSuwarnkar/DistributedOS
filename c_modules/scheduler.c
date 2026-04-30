/*
 * scheduler.c  –  CPU Scheduling Algorithms
 *
 * Function: run_scheduler()
 *   Picks the index (0-based) of the next process to dispatch from the
 *   ready queue using the chosen algorithm.
 *
 * Parameters:
 *   algo       – "FCFS" | "SJF" | "PRIORITY" | "RR"
 *   n          – number of processes in the ready queue
 *   burst[]    – burst times (durations) of each process
 *   priority[] – priority values of each process (lower = higher priority)
 *   rr_last    – index of the last process dispatched (used for Round Robin);
 *                pass -1 on first call
 *
 * Returns:
 *   Index (0..n-1) of the selected process
 */

#ifndef SCHEDULER_C
#define SCHEDULER_C

#include <string.h>

int run_scheduler(const char *algo, int n, int burst[], int priority[], int rr_last)
{
    if(n <= 0) return 0;

    /* ── FCFS: first-in, first-served → always index 0 ── */
    if(strcmp(algo, "FCFS") == 0)
    {
        return 0;
    }

    /* ── SJF: pick process with smallest burst time ── */
    if(strcmp(algo, "SJF") == 0)
    {
        int idx = 0;

        for(int i = 1; i < n; i++)
        {
            if(burst[i] < burst[idx])
                idx = i;
        }

        return idx;
    }

    /* ── PRIORITY: pick process with lowest priority number ── */
    if(strcmp(algo, "PRIORITY") == 0)
    {
        int idx = 0;

        for(int i = 1; i < n; i++)
        {
            if(priority[i] < priority[idx])
                idx = i;
            else if(priority[i] == priority[idx] && burst[i] < burst[idx])
                idx = i;
        }

        return idx;
    }

    /* ── Round Robin: next after the last dispatched ── */
    if(strcmp(algo, "RR") == 0)
    {
        return (rr_last + 1) % n;
    }

    /* Fallback to FCFS */
    return 0;
}

#endif /* SCHEDULER_C */