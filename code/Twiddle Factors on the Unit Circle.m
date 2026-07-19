clc;
clear;
close all;

figure('Position',[100 20 750 950]);
axis off

w = 0.42;
h = 0.07;
x = 0.29;

Y = [0.90 0.80 0.70 0.60 0.50 0.40 0.30 0.20];

txt = {
'Time-Domain Input Signal'
'Analog-to-Digital Sampling'
'Bit-Reversal Ordering'
'Butterfly Computation Stage 1'
'Complex Addition / Subtraction'
'Twiddle Factor Multiplication'
'Butterfly Final Stage'
'Frequency-Domain Spectrum'
};

color = [
0.85 0.93 1.00
0.90 1.00 0.90
1.00 0.95 0.85
1.00 0.95 0.85
1.00 0.90 0.90
0.95 0.90 1.00
1.00 0.95 0.85
0.85 1.00 1.00
];

for i=1:8

annotation('rectangle',...
    [x Y(i) w h],...
    'LineWidth',2,...
    'FaceColor',color(i,:));

annotation('textbox',...
    [x Y(i) w h],...
    'String',txt{i},...
    'FontWeight','bold',...
    'FontSize',12,...
    'HorizontalAlignment','center',...
    'VerticalAlignment','middle',...
    'EdgeColor','none');

end

%% Arrows

for i=1:7

annotation('arrow',...
    [0.50 0.50],...
    [Y(i) Y(i)-0.03],...
    'LineWidth',2);

end

%% Title

annotation('textbox',...
[0.15 0.96 0.7 0.04],...
'String','Basic Processing Flow of the Fast Fourier Transform (FFT)',...
'HorizontalAlignment','center',...
'FontWeight','bold',...
'FontSize',17,...
'EdgeColor','none');

exportgraphics(gcf,'FFT_FLOW.png','Resolution',300);