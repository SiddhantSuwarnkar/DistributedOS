#include <stdio.h>

int bankers(int p, int r, int max[p][r], int alloc[p][r], int avail[r])
{
    int need[p][r];
    int finish[p];
    int safe[p];
    int count = 0;

    for(int i=0;i<p;i++)
        finish[i] = 0;

    for(int i=0;i<p;i++)
        for(int j=0;j<r;j++)
            need[i][j] = max[i][j] - alloc[i][j];

    while(count < p)
    {
        int found = 0;

        for(int i=0;i<p;i++)
        {
            if(finish[i]==0)
            {
                int possible = 1;

                for(int j=0;j<r;j++)
                {
                    if(need[i][j] > avail[j])
                    {
                        possible = 0;
                        break;
                    }
                }

                if(possible)
                {
                    for(int j=0;j<r;j++)
                        avail[j] += alloc[i][j];

                    safe[count++] = i;
                    finish[i] = 1;
                    found = 1;
                }
            }
        }

        if(found==0)
        {
            printf("\nSystem is NOT in safe state\n");
            return 0;
        }
    }

    printf("\nSystem is in SAFE state\nSafe sequence: ");

    for(int i=0;i<p;i++)
        printf("P%d ",safe[i]);

    printf("\n");

    return 1;
}