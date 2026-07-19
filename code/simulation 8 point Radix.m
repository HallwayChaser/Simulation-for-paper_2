clc; clear; close all;

figure('Color','w','Position',[100 100 1100 420]);
hold on; axis off;

N = 8;
stages = 4; % input + 3 FFT stages
xpos = [0 1.8 3.6 5.4];
ypos = linspace(7,0,N);

% Draw input and output labels
for i = 1:N
    text(-0.35, ypos(i), sprintf('x[%d]', i-1), ...
        'HorizontalAlignment','right','FontSize',10);
    text(5.75, ypos(i), sprintf('X[%d]', i-1), ...
        'HorizontalAlignment','left','FontSize',10);
end

% Draw horizontal lines
for i = 1:N
    plot([xpos(1), xpos(end)], [ypos(i), ypos(i)], 'k', 'LineWidth', 1);
end

% Stage 1 butterflies: distance 1
pairs1 = [1 2; 3 4; 5 6; 7 8];

% Stage 2 butterflies: distance 2
pairs2 = [1 3; 2 4; 5 7; 6 8];

% Stage 3 butterflies: distance 4
pairs3 = [1 5; 2 6; 3 7; 4 8];

draw_stage(pairs1, xpos(1), xpos(2), ypos, {'1','-1','1','-1','1','-1','1','-1'});
draw_stage(pairs2, xpos(2), xpos(3), ypos, {'1','W_4^1','1','W_4^1','1','W_4^1','1','W_4^1'});
draw_stage(pairs3, xpos(3), xpos(4), ypos, {'1','W_8^1','W_8^2','W_8^3','1','W_8^1','W_8^2','W_8^3'});

% Stage titles
text(0.9, 7.65, 'Stage 1', 'HorizontalAlignment','center','FontWeight','bold');
text(2.7, 7.65, 'Stage 2', 'HorizontalAlignment','center','FontWeight','bold');
text(4.5, 7.65, 'Stage 3', 'HorizontalAlignment','center','FontWeight','bold');

title('8-point Radix-2 FFT Signal Flow Graph','FontSize',14,'FontWeight','bold');

saveas(gcf,'fft8_radix2_signal_flow_graph.png');

function draw_stage(pairs, x1, x2, ypos, labels)
for p = 1:size(pairs,1)
    a = pairs(p,1);
    b = pairs(p,2);

    ya = ypos(a);
    yb = ypos(b);

    % Upper and lower crossing lines
    plot([x1 x2], [ya ya], 'k', 'LineWidth', 1);
    plot([x1 x2], [yb yb], 'k', 'LineWidth', 1);
    plot([x1 x2], [ya yb], 'k', 'LineWidth', 1);
    plot([x1 x2], [yb ya], 'k', 'LineWidth', 1);

    % Arrow heads
    plot(x2, ya, 'k>', 'MarkerSize', 5, 'MarkerFaceColor','k');
    plot(x2, yb, 'k>', 'MarkerSize', 5, 'MarkerFaceColor','k');

    % Twiddle labels
    text((x1+x2)/2, yb-0.22, labels{b}, ...
        'HorizontalAlignment','center', ...
        'FontSize',9, ...
        'Interpreter','tex');
end
end
