/*
 * sim_runner.c  –  Unified C algorithm runner
 *
 * Called by coordinator.py via subprocess.
 *
 * Commands
 * --------
 * memory   <algo> <blocks,csv> <size>
 *   Output: MEMORY|<1-based idx>|<remaining>   or  MEMORY|0|0 (no fit)
 *
 * disk     <algo> <head> <requests,csv>
 *   Output: DISK|<order,csv>|<total_seek>
 *
 * scheduler <algo> <bursts,csv> <priorities,csv> <rr_last>
 *   Output: SCHED|<chosen_idx>
 *
 * bankers  <P> <R> <avail,csv> <max,csv> <alloc,csv>
 *   Output: BANKERS|SAFE|<seq,csv>   or  BANKERS|UNSAFE
 *
 * deadlock <P> <R> <avail,csv> <alloc,csv> <req,csv>
 *   Output: DEADLOCK|<count>|<dead_pids,csv>   or  DEADLOCK|0|
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "memory.c"
#include "disk.c"
#include "scheduler.c"
#include "bankers.c"
#include "deadlock.c"

/* ── helpers ── */

static int parse_csv(char *txt, int arr[])
{
    if(!txt || txt[0] == '\0') return 0;
    int count = 0;
    char *token = strtok(txt, ",");

    while(token != NULL)
    {
        arr[count++] = atoi(token);
        token = strtok(NULL, ",");
    }
    return count;
}

/* ══════════════════════════════════════════════════════════════════════ */

int main(int argc, char *argv[])
{
    if(argc < 2) return 0;

    /* ── MEMORY ── */
    if(strcmp(argv[1], "memory") == 0)
    {
        if(argc < 5) return 0;

        char algo[50];
        strcpy(algo, argv[2]);

        char block_txt[500];
        strcpy(block_txt, argv[3]);

        int size     = atoi(argv[4]);
        int nf_last  = (argc >= 6) ? atoi(argv[5]) : 0;  /* NextFit last pos */

        int blocks[100];
        int m = parse_csv(block_txt, blocks);

        int idx     = -1;
        int nf_next = 0;   /* new NextFit position to echo back */

        if(strcmp(algo, "FirstFit") == 0)
            idx = first_fit(blocks, m, size);
        else if(strcmp(algo, "BestFit") == 0)
            idx = best_fit(blocks, m, size);
        else if(strcmp(algo, "WorstFit") == 0)
            idx = worst_fit(blocks, m, size);
        else if(strcmp(algo, "NextFit") == 0)
            idx = next_fit(blocks, m, size, nf_last, &nf_next);
        else
            idx = first_fit(blocks, m, size);   /* default */

        if(idx == -1)
            printf("MEMORY|0|0|%d\n", nf_next);
        else
        {
            blocks[idx] -= size;
            /* Format: MEMORY|<1-based-idx>|<remaining>|<next_nf_pos> */
            printf("MEMORY|%d|%d|%d\n", idx + 1, blocks[idx], nf_next);
        }
    }

    /* ── DISK ── */
    else if(strcmp(argv[1], "disk") == 0)
    {
        if(argc < 5) return 0;

        char algo[50];
        strcpy(algo, argv[2]);

        int head = atoi(argv[3]);

        char req_txt[500];
        strcpy(req_txt, argv[4]);

        int cyl_max = (argc >= 6) ? atoi(argv[5]) : 200;  /* cylinder range */

        int req[100], order[100];
        int n = parse_csv(req_txt, req);
        int seek = 0;

        if(strcmp(algo, "FCFS") == 0)       seek = disk_fcfs(req, n, head, order);
        else if(strcmp(algo, "SSTF") == 0)  seek = disk_sstf(req, n, head, order);
        else if(strcmp(algo, "SCAN") == 0)  seek = disk_scan(req, n, head, order);
        else if(strcmp(algo, "CSCAN") == 0) seek = disk_cscan(req, n, head, order, cyl_max);
        else                                seek = disk_fcfs(req, n, head, order);

        printf("DISK|");
        for(int i = 0; i < n; i++)
        {
            printf("%d", order[i]);
            if(i < n - 1) printf(",");
        }
        printf("|%d\n", seek);
    }

    /* ── SCHEDULER ── */
    else if(strcmp(argv[1], "scheduler") == 0)
    {
        /*  argv[2] = algo
            argv[3] = bursts csv
            argv[4] = priorities csv
            argv[5] = rr_last index (-1 for first call)           */
        if(argc < 6) { printf("SCHED|0\n"); return 0; }

        char algo[20];
        strcpy(algo, argv[2]);

        char burst_txt[2000];
        strcpy(burst_txt, argv[3]);

        char prio_txt[2000];
        strcpy(prio_txt, argv[4]);

        int rr_last = atoi(argv[5]);

        int bursts[500], priorities[500];
        int n1 = parse_csv(burst_txt, bursts);
        int n2 = parse_csv(prio_txt,  priorities);

        int n = (n1 < n2) ? n1 : n2;
        if(n <= 0) { printf("SCHED|0\n"); return 0; }

        int chosen = run_scheduler(algo, n, bursts, priorities, rr_last);
        printf("SCHED|%d\n", chosen);
    }

    /* ── BANKER'S SAFETY CHECK ── */
    else if(strcmp(argv[1], "bankers") == 0)
    {
        /*  argv[2] = P (process count)
            argv[3] = R (resource types)
            argv[4] = available csv (length R)
            argv[5] = max csv       (length P*R, row-major)
            argv[6] = alloc csv     (length P*R, row-major)   */
        if(argc < 7) { printf("BANKERS|UNSAFE\n"); return 0; }

        int P = atoi(argv[2]);
        int R = atoi(argv[3]);

        char av_txt[500];   strcpy(av_txt,   argv[4]);
        char max_txt[5000]; strcpy(max_txt,  argv[5]);
        char al_txt[5000];  strcpy(al_txt,   argv[6]);

        int avail[10], max_flat[100], alloc_flat[100];
        parse_csv(av_txt,  avail);
        parse_csv(max_txt, max_flat);
        parse_csv(al_txt,  alloc_flat);

        int safe = bankers_is_safe(P, R, avail, max_flat, alloc_flat);

        if(safe)
        {
            /* Recompute safe sequence to display */
            int work[10], finish[10], seq[10], cnt = 0;
            int need[10][10];

            for(int j = 0; j < R; j++) work[j] = avail[j];
            for(int i = 0; i < P; i++)
            {
                finish[i] = 0;
                for(int j = 0; j < R; j++)
                    need[i][j] = max_flat[i*R+j] - alloc_flat[i*R+j];
            }

            while(cnt < P)
            {
                int found = 0;
                for(int i = 0; i < P; i++)
                {
                    if(!finish[i])
                    {
                        int ok = 1;
                        for(int j = 0; j < R; j++)
                            if(need[i][j] > work[j]) { ok = 0; break; }
                        if(ok)
                        {
                            for(int j = 0; j < R; j++) work[j] += alloc_flat[i*R+j];
                            seq[cnt++] = i;
                            finish[i] = 1;
                            found = 1;
                        }
                    }
                }
                if(!found) break;
            }

            printf("BANKERS|SAFE|");
            for(int i = 0; i < cnt; i++)
            {
                printf("%d", seq[i]);
                if(i < cnt - 1) printf(",");
            }
            printf("\n");
        }
        else
        {
            printf("BANKERS|UNSAFE\n");
        }
    }

    /* ── DEADLOCK DETECTION ── */
    else if(strcmp(argv[1], "deadlock") == 0)
    {
        /*  argv[2] = P
            argv[3] = R
            argv[4] = available csv
            argv[5] = alloc csv (P*R row-major)
            argv[6] = request csv (P*R row-major)   */
        if(argc < 7) { printf("DEADLOCK|0|\n"); return 0; }

        int P = atoi(argv[2]);
        int R = atoi(argv[3]);

        char av_txt[500];    strcpy(av_txt,   argv[4]);
        char al_txt[5000];   strcpy(al_txt,   argv[5]);
        char req_txt[5000];  strcpy(req_txt,  argv[6]);

        int avail[10], alloc_flat[100], req_flat[100], dead[100];
        parse_csv(av_txt,  avail);
        parse_csv(al_txt,  alloc_flat);
        parse_csv(req_txt, req_flat);

        int n_dead = detect_deadlock(P, R, avail, alloc_flat, req_flat, dead);

        printf("DEADLOCK|%d|", n_dead);
        for(int i = 0; i < n_dead; i++)
        {
            printf("%d", dead[i]);
            if(i < n_dead - 1) printf(",");
        }
        printf("\n");
    }

    return 0;
}
