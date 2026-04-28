#include <stdio.h>
#include <string.h>

#define BLOCKS 5

int memory[BLOCKS] = {100, 500, 200, 300, 600};
int process_size = 212;
int last_pos = 0;

int first_fit()
{
    for(int i = 0; i < BLOCKS; i++)
    {
        if(memory[i] >= process_size)
            return i;
    }
    return -1;
}

int best_fit()
{
    int idx = -1;

    for(int i = 0; i < BLOCKS; i++)
    {
        if(memory[i] >= process_size)
        {
            if(idx == -1 || memory[i] < memory[idx])
                idx = i;
        }
    }
    return idx;
}

int worst_fit()
{
    int idx = -1;

    for(int i = 0; i < BLOCKS; i++)
    {
        if(memory[i] >= process_size)
        {
            if(idx == -1 || memory[i] > memory[idx])
                idx = i;
        }
    }
    return idx;
}

int next_fit()
{
    for(int count = 0; count < BLOCKS; count++)
    {
        int i = (last_pos + count) % BLOCKS;

        if(memory[i] >= process_size)
        {
            last_pos = i + 1;
            return i;
        }
    }
    return -1;
}

int main(int argc, char *argv[])
{
    int block = -1;

    if(argc < 2)
    {
        printf("Usage");
        return 0;
    }

    if(strcmp(argv[1], "FirstFit") == 0)
        block = first_fit();

    else if(strcmp(argv[1], "BestFit") == 0)
        block = best_fit();

    else if(strcmp(argv[1], "WorstFit") == 0)
        block = worst_fit();

    else if(strcmp(argv[1], "NextFit") == 0)
        block = next_fit();

    else
    {
        printf("Invalid");
        return 0;
    }

    if(block == -1)
        printf("No Block");

    else
        printf("Block %d", block + 1);

    return 0;
}