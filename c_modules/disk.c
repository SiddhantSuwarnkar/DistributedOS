#include <stdio.h>
#include <stdlib.h>

int abs_val(int x)
{
    return x < 0 ? -x : x;
}

int disk_fcfs(int req[], int n, int head, int order[])
{
    int seek = 0;
    int cur = head;

    for(int i=0;i<n;i++)
    {
        order[i] = req[i];
        seek += abs_val(req[i] - cur);
        cur = req[i];
    }
    return seek;
}

int disk_sstf(int req[], int n, int head, int order[])
{
    int seek = 0;
    int cur = head;
    int used[100] = {0};

    for(int k=0;k<n;k++)
    {
        int idx = -1;
        int best = 100000;

        for(int i=0;i<n;i++)
        {
            if(!used[i])
            {
                int d = abs_val(req[i] - cur);
                if(d < best)
                {
                    best = d;
                    idx = i;
                }
            }
        }

        used[idx] = 1;
        order[k] = req[idx];
        seek += abs_val(req[idx] - cur);
        cur = req[idx];
    }
    return seek;
}

int disk_scan(int req[], int n, int head, int order[])
{
    /* SCAN (Elevator): service requests going toward higher cylinders first,
       then reverse and service remaining requests toward lower cylinders. */
    int seek = 0;
    int cur  = head;

    /* Sort requests ascending */
    int sorted[100];
    for(int i = 0; i < n; i++) sorted[i] = req[i];
    for(int i = 0; i < n - 1; i++)
        for(int j = 0; j < n - i - 1; j++)
            if(sorted[j] > sorted[j+1]) {
                int tmp = sorted[j]; sorted[j] = sorted[j+1]; sorted[j+1] = tmp;
            }

    /* Find split point: first index >= head */
    int start_idx = 0;
    while(start_idx < n && sorted[start_idx] < head) start_idx++;

    int k = 0;
    /* Pass 1: move toward higher cylinders */
    for(int i = start_idx; i < n; i++) {
        order[k++] = sorted[i];
        seek += abs_val(sorted[i] - cur);
        cur   = sorted[i];
    }
    /* Pass 2: reverse, move toward lower cylinders */
    for(int i = start_idx - 1; i >= 0; i--) {
        order[k++] = sorted[i];
        seek += abs_val(sorted[i] - cur);
        cur   = sorted[i];
    }
    return seek;
}

int disk_cscan(int req[], int n, int head, int order[], int cyl_max)
{
    /* C-SCAN: move right serving requests, then jump back to cylinder 0
       and continue serving remaining requests. The wrap-around jump
       (from last served rightward cylinder to 0, then to first request)
       IS counted in the seek distance. */
    int seek = 0;
    int cur = head;

    /* Sort requests ascending */
    int sorted[100];
    for (int i=0; i<n; i++) sorted[i] = req[i];
    for (int i=0; i<n-1; i++) {
        for (int j=0; j<n-i-1; j++) {
            if (sorted[j] > sorted[j+1]) {
                int temp = sorted[j];
                sorted[j] = sorted[j+1];
                sorted[j+1] = temp;
            }
        }
    }

    int start_idx = 0;
    while(start_idx < n && sorted[start_idx] < head) start_idx++;

    int k = 0;
    /* Moving right – serve all requests >= head */
    for(int i=start_idx; i<n; i++) {
        order[k++] = sorted[i];
        seek += abs_val(sorted[i] - cur);
        cur = sorted[i];
    }

    if(start_idx > 0) {
        /* Wrap-around: go to end of disk then back to cylinder 0 */
        seek += abs_val(cyl_max - cur);  /* head → max cylinder */
        seek += cyl_max;                 /* max cylinder → 0     */
        cur = 0;

        /* Serve remaining requests from the beginning */
        for(int i=0; i<start_idx; i++) {
            order[k++] = sorted[i];
            seek += abs_val(sorted[i] - cur);
            cur = sorted[i];
        }
    }
    return seek;
}