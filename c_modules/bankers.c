#include <stdio.h>

#define MAXP 10
#define MAXR 10

int main()
{
    int p, r;
    int max[MAXP][MAXR];
    int alloc[MAXP][MAXR];
    int need[MAXP][MAXR];
    int avail[MAXR];
    int work[MAXR];

    int finish[MAXP] = {0};
    int safe[MAXP];
    int count = 0;

    scanf("%d %d", &p, &r);

    for(int i = 0; i < p; i++)
        for(int j = 0; j < r; j++)
            scanf("%d", &max[i][j]);

    for(int i = 0; i < p; i++)
        for(int j = 0; j < r; j++)
            scanf("%d", &alloc[i][j]);

    for(int j = 0; j < r; j++)
        scanf("%d", &avail[j]);

    for(int j = 0; j < r; j++)
        work[j] = avail[j];

    for(int i = 0; i < p; i++)
        for(int j = 0; j < r; j++)
            need[i][j] = max[i][j] - alloc[i][j];

    printf("BANKERS ALGORITHM\n\n");

    printf("MAX MATRIX\n");
    for(int i = 0; i < p; i++)
    {
        for(int j = 0; j < r; j++)
            printf("%d ", max[i][j]);
        printf("\n");
    }

    printf("\nALLOCATION MATRIX\n");
    for(int i = 0; i < p; i++)
    {
        for(int j = 0; j < r; j++)
            printf("%d ", alloc[i][j]);
        printf("\n");
    }

    printf("\nNEED MATRIX\n");
    for(int i = 0; i < p; i++)
    {
        for(int j = 0; j < r; j++)
            printf("%d ", need[i][j]);
        printf("\n");
    }

    printf("\nAVAILABLE\n");
    for(int j = 0; j < r; j++)
        printf("%d ", avail[j]);
    printf("\n\n");

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
                    printf("P%d can execute. Work: ", i);

                    for(int j = 0; j < r; j++)
                    {
                        work[j] += alloc[i][j];
                        printf("%d ", work[j]);
                    }

                    printf("\n");

                    safe[count++] = i;
                    finish[i] = 1;
                    found = 1;
                }
            }
        }

        if(found == 0)
        {
            printf("\nSYSTEM IS UNSAFE\n");
            return 0;
        }
    }

    printf("\nSYSTEM IS SAFE\n");
    printf("SAFE SEQUENCE: ");

    for(int i = 0; i < p; i++)
        printf("P%d ", safe[i]);

    printf("\n");

    return 0;
}