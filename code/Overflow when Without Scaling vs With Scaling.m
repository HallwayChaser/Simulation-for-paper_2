clc;
clear;
close all;

%% ==========================================================
% PARAMETERS
%% ==========================================================

Fs = 1000;                 % Sampling frequency
N  = 256;                  % FFT length

t = (0:N-1)/Fs;

%% ==========================================================
% INPUT SIGNAL
%% ==========================================================

A = 2.2;                   % Large amplitude to cause overflow
f = 50;

x = A*sin(2*pi*f*t);

%% ==========================================================
% FIXED-POINT (8-bit)
%% ==========================================================

bits = 8;

scale = 2^(bits-1)-1;

%% ==========================================================
% WITHOUT SCALING
%% ==========================================================

x_noScale = round(x*scale);

x_noScale(x_noScale>127)=127;
x_noScale(x_noScale<-128)=-128;

x_noScale = x_noScale/scale;

%% ==========================================================
% WITH SCALING
%% ==========================================================

ScaleFactor = 2;

x_scale = x/ScaleFactor;

x_scale = round(x_scale*scale);

x_scale(x_scale>127)=127;
x_scale(x_scale<-128)=-128;

x_scale = x_scale/scale;

%% ==========================================================
% FFT
%% ==========================================================

FFT_NoScale = abs(fft(x_noScale));

FFT_Scale = abs(fft(x_scale));

%% ==========================================================
% FIGURE
%% ==========================================================

figure('Position',[100 100 1300 750]);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,1)

plot(t,x,'k','LineWidth',2)

hold on

plot(t,x_noScale,'r','LineWidth',2)

grid on
box on

xlim([0 0.08])

title('Without Scaling')

xlabel('Time (s)')
ylabel('Amplitude')

legend('Original','Overflow')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,2)

plot(t,x,'k','LineWidth',2)

hold on

plot(t,x_scale,'b','LineWidth',2)

grid on
box on

xlim([0 0.08])

title('With Scaling')

xlabel('Time (s)')
ylabel('Amplitude')

legend('Original','Scaled')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,3)

plot(FFT_NoScale,'r','LineWidth',2)

grid on
box on

xlim([0 N/2])

title('FFT without Scaling')

xlabel('Frequency Bin')
ylabel('Magnitude')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,4)

plot(FFT_Scale,'b','LineWidth',2)

grid on
box on

xlim([0 N/2])

title('FFT with Scaling')

xlabel('Frequency Bin')
ylabel('Magnitude')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
sgtitle('Overflow Comparison: Without Scaling vs With Scaling',...
    'FontSize',20,...
    'FontWeight','bold')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
annotation('textbox',...
[0.30 0.01 0.42 0.08],...
'String',...
sprintf(['Amplitude = %.1f     Word Length = %d-bit     Scaling Factor = 1/%d'],...
A,bits,ScaleFactor),...
'HorizontalAlignment','center',...
'FontSize',12,...
'BackgroundColor','white',...
'EdgeColor','black');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
exportgraphics(gcf,...
'Overflow_vs_Scaling.png',...
'Resolution',300);