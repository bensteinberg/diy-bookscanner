#!/bin/bash

num=1
for a in *.JPG; do
    b=$(printf "%04d.jpg" $num)
    cp $a ../sorted/$b
    num=$[num+2]
done
