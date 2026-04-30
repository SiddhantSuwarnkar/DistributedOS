#include <stdio.h>

int first_fit(int blocks[], int m, int size)
{
    for(int i = 0; i < m; i++)
        if(blocks[i] >= size)
            return i;
    return -1;
}

int best_fit(int blocks[], int m, int size)
{
    int idx = -1;
    for(int i = 0; i < m; i++)
    {
        if(blocks[i] >= size)
        {
            if(idx == -1 || blocks[i] < blocks[idx])
                idx = i;
        }
    }
    return idx;
}

int worst_fit(int blocks[], int m, int size)
{
    int idx = -1;
    for(int i = 0; i < m; i++)
    {
        if(blocks[i] >= size)
        {
            if(idx == -1 || blocks[i] > blocks[idx])
                idx = i;
        }
    }
    return idx;
}

/*
 * next_fit: allocate from blocks[], starting search at last_pos.
 *           Sets *new_pos to the position AFTER the chosen block
 *           so the caller can persist it across calls.
 */
int next_fit(int blocks[], int m, int size, int last_pos, int *new_pos)
{
    for(int c = 0; c < m; c++)
    {
        int i = (last_pos + c) % m;
        if(blocks[i] >= size)
        {
            *new_pos = (i + 1) % m;
            return i;
        }
    }
    return -1;
}