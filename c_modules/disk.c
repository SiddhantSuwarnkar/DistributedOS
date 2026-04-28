#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define N 8
#define MAX_TRACK 199

int req[N] = {98, 183, 37, 122, 14, 124, 65, 67};
int head = 53;

int abs_val(int x)
{
    return x < 0 ? -x : x;
}

int fcfs()
{
    int seek = 0;
    int cur = head;

    for(int i = 0; i < N; i++)
    {
        seek += abs_val(req[i] - cur);
        cur = req[i];
    }

    return seek;
}

int sstf()
{
    int seek = 0;
    int cur = head;
    int visited[N] = {0};

    for(int done = 0; done < N; done++)
    {
        int idx = -1;
        int best = 100000;

        for(int i = 0; i < N; i++)
        {
            if(!visited[i])
            {
                int d = abs_val(req[i] - cur);

                if(d < best)
                {
                    best = d;
                    idx = i;
                }
            }
        }

        visited[idx] = 1;
        seek += abs_val(req[idx] - cur);
        cur = req[idx];
    }

    return seek;
}

int scan()
{
    int seek = 0;
    int cur = head;
    int done[N] = {0};

    while(1)
    {
        int idx = -1;
        int best = 100000;

        for(int i = 0; i < N; i++)
        {
            if(!done[i] && req[i] >= cur)
            {
                int d = req[i] - cur;
                if(d < best)
                {
                    best = d;
                    idx = i;
                }
            }
        }

        if(idx == -1)
            break;

        seek += req[idx] - cur;
        cur = req[idx];
        done[idx] = 1;
    }

    seek += MAX_TRACK - cur;
    cur = MAX_TRACK;

    while(1)
    {
        int idx = -1;
        int best = 100000;

        for(int i = 0; i < N; i++)
        {
            if(!done[i])
            {
                int d = cur - req[i];
                if(d >= 0 && d < best)
                {
                    best = d;
                    idx = i;
                }
            }
        }

        if(idx == -1)
            break;

        seek += cur - req[idx];
        cur = req[idx];
        done[idx] = 1;
    }

    return seek;
}

int cscan()
{
    int seek = 0;
    int cur = head;
    int done[N] = {0};

    while(1)
    {
        int idx = -1;
        int best = 100000;

        for(int i = 0; i < N; i++)
        {
            if(!done[i] && req[i] >= cur)
            {
                int d = req[i] - cur;
                if(d < best)
                {
                    best = d;
                    idx = i;
                }
            }
        }

        if(idx == -1)
            break;

        seek += req[idx] - cur;
        cur = req[idx];
        done[idx] = 1;
    }

    seek += MAX_TRACK - cur;
    seek += MAX_TRACK;
    cur = 0;

    while(1)
    {
        int idx = -1;
        int best = 100000;

        for(int i = 0; i < N; i++)
        {
            if(!done[i])
            {
                int d = req[i] - cur;
                if(d >= 0 && d < best)
                {
                    best = d;
                    idx = i;
                }
            }
        }

        if(idx == -1)
            break;

        seek += req[idx] - cur;
        cur = req[idx];
        done[idx] = 1;
    }

    return seek;
}

int main(int argc, char *argv[])
{
    if(argc < 2)
    {
        printf("Usage");
        return 0;
    }

    if(strcmp(argv[1], "FCFS") == 0)
        printf("Seek %d", fcfs());

    else if(strcmp(argv[1], "SCAN") == 0)
        printf("Seek %d", scan());

    else if(strcmp(argv[1], "CSCAN") == 0)
        printf("Seek %d", cscan());

    else if(strcmp(argv[1], "SSTF") == 0)
        printf("Seek %d", sstf());

    else
        printf("Invalid");

    return 0;
}