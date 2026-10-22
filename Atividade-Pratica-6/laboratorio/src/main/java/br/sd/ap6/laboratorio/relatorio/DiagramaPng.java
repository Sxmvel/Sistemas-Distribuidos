package br.sd.ap6.laboratorio.relatorio;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;
import java.awt.Polygon;
import java.awt.Rectangle;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import javax.imageio.ImageIO;

public final class DiagramaPng {

    private record Estilo(Color fundo, Color borda, boolean tracejado) {
    }

    private static final int larguraCaixa = 136;
    private static final int alturaCaixa = 80;
    private static final int espacoHorizontal = 34;
    private static final int espacoVertical = 70;
    private static final int margem = 28;
    private static final int alturaTitulo = 44;
    private static final int alturaRotulo = 30;
    private static final int alturaLinhaLegenda = 22;

    private static final Color fundoDaImagem = Color.white;
    private static final Color texto = new Color(0x22, 0x22, 0x2e);
    private static final Color textoSecundario = new Color(0x5a, 0x5a, 0x6e);
    private static final Estilo tronco = new Estilo(new Color(0xec, 0xec, 0xf2), new Color(0x6b, 0x6b, 0x80), false);
    private static final Estilo mantido = new Estilo(new Color(0xdc, 0xea, 0xfe), new Color(0x2f, 0x6f, 0xdb), false);
    private static final Estilo descartado = new Estilo(new Color(0xfe, 0xea, 0xd8), new Color(0xd2, 0x6b, 0x16), true);

    private static final Font fonteTitulo = new Font(Font.SANS_SERIF, Font.BOLD, 22);
    private static final Font fonteCaixa = new Font(Font.SANS_SERIF, Font.BOLD, 16);
    private static final Font fonteDados = new Font(Font.SANS_SERIF, Font.PLAIN, 16);
    private static final Font fonteHash = new Font(Font.MONOSPACED, Font.PLAIN, 15);
    private static final Font fonteRotulo = new Font(Font.SANS_SERIF, Font.BOLD, 17);
    private static final Font fonteSituacao = new Font(Font.SANS_SERIF, Font.PLAIN, 16);
    private static final Font fonteLegenda = new Font(Font.SANS_SERIF, Font.PLAIN, 15);

    public void desenhar(Diagrama diagrama, Path arquivo) throws IOException {
        var colunas = diagrama.tronco().size()
                + Math.max(diagrama.superior().caixas().size(), diagrama.inferior().caixas().size());
        var largura = margem * 2 + colunas * (larguraCaixa + espacoHorizontal) - espacoHorizontal;
        var legenda = quebrarLegenda(diagrama.legenda(), largura - 2 * margem);
        var ySuperior = margem + alturaTitulo + alturaRotulo;
        var yTronco = ySuperior + alturaCaixa + espacoVertical;
        var yInferior = yTronco + alturaCaixa + espacoVertical;
        var yLegenda = yInferior + alturaCaixa + 36;
        var altura = yLegenda + legenda.size() * alturaLinhaLegenda + margem;

        var imagem = new BufferedImage(largura, altura, BufferedImage.TYPE_INT_RGB);
        var g = imagem.createGraphics();
        try {
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
            g.setColor(fundoDaImagem);
            g.fillRect(0, 0, largura, altura);

            g.setColor(texto);
            g.setFont(fonteTitulo);
            g.drawString(diagrama.titulo(), margem, margem + 22);

            var caixasDoTronco = desenharLinha(g, diagrama.tronco(), 0, yTronco, tronco, null);
            var ultimoDoTronco = caixasDoTronco.getLast();
            desenharRamo(g, diagrama.superior(), diagrama.tronco().size(), ySuperior, ultimoDoTronco);
            desenharRamo(g, diagrama.inferior(), diagrama.tronco().size(), yInferior, ultimoDoTronco);

            g.setFont(fonteLegenda);
            g.setColor(textoSecundario);
            for (int i = 0; i < legenda.size(); i++) {
                g.drawString(legenda.get(i), margem, yLegenda + 16 + i * alturaLinhaLegenda);
            }
        } finally {
            g.dispose();
        }
        ImageIO.write(imagem, "png", arquivo.toFile());
    }

    private void desenharRamo(Graphics2D g, Ramo ramo, int colunaInicial, int y, Rectangle pai) {
        var estilo = ramo.mantido() ? mantido : descartado;
        var caixas = desenharLinha(g, ramo.caixas(), colunaInicial, y, estilo, pai);
        var xRotulo = caixas.getFirst().x;
        var yRotulo = y - 12;
        g.setColor(estilo.borda());
        g.setFont(fonteRotulo);
        g.drawString(ramo.nome(), xRotulo, yRotulo);
        var larguraNome = g.getFontMetrics().stringWidth(ramo.nome());
        g.setColor(textoSecundario);
        g.setFont(fonteSituacao);
        g.drawString("— " + ramo.situacao(), xRotulo + larguraNome + 8, yRotulo);
    }

    private List<Rectangle> desenharLinha(Graphics2D g, List<Caixa> caixas, int colunaInicial, int y,
                                          Estilo estilo, Rectangle pai) {
        var desenhadas = new ArrayList<Rectangle>();
        var anterior = pai;
        for (int i = 0; i < caixas.size(); i++) {
            var x = margem + (colunaInicial + i) * (larguraCaixa + espacoHorizontal);
            var retangulo = new Rectangle(x, y, larguraCaixa, alturaCaixa);
            if (anterior != null) {
                seta(g, retangulo, anterior, estilo.borda());
            }
            caixa(g, retangulo, caixas.get(i), estilo);
            desenhadas.add(retangulo);
            anterior = retangulo;
        }
        return desenhadas;
    }

    private void caixa(Graphics2D g, Rectangle r, Caixa caixa, Estilo estilo) {
        g.setColor(estilo.fundo());
        g.fillRoundRect(r.x, r.y, r.width, r.height, 12, 12);
        g.setColor(estilo.borda());
        g.setStroke(estilo.tracejado()
                ? new BasicStroke(2.2f, BasicStroke.CAP_BUTT, BasicStroke.JOIN_ROUND, 1f, new float[]{7f, 5f}, 0f)
                : new BasicStroke(2.2f));
        g.drawRoundRect(r.x, r.y, r.width, r.height, 12, 12);
        g.setStroke(new BasicStroke(1f));

        g.setColor(texto);
        g.setFont(fonteCaixa);
        g.drawString(caixa.titulo(), r.x + 11, r.y + 23);
        g.setFont(fonteDados);
        g.drawString(caixa.linhaPrincipal(), r.x + 11, r.y + 46);
        g.setColor(textoSecundario);
        g.setFont(fonteHash);
        g.drawString(caixa.linhaSecundaria(), r.x + 11, r.y + 67);
    }

    private void seta(Graphics2D g, Rectangle filho, Rectangle pai, Color cor) {
        var x1 = filho.x;
        var y1 = filho.y + filho.height / 2;
        var x2 = pai.x + pai.width;
        var y2 = pai.y + pai.height / 2;
        g.setColor(cor);
        g.setStroke(new BasicStroke(2f));
        g.drawLine(x1, y1, x2, y2);
        var angulo = Math.atan2(y2 - y1, x2 - x1);
        var ponta = new Polygon();
        ponta.addPoint(x2, y2);
        ponta.addPoint((int) Math.round(x2 - 11 * Math.cos(angulo - 0.4)), (int) Math.round(y2 - 11 * Math.sin(angulo - 0.4)));
        ponta.addPoint((int) Math.round(x2 - 11 * Math.cos(angulo + 0.4)), (int) Math.round(y2 - 11 * Math.sin(angulo + 0.4)));
        g.fillPolygon(ponta);
        g.setStroke(new BasicStroke(1f));
    }

    private List<String> quebrarLegenda(List<String> paragrafos, int larguraMaxima) {
        var medidor = new BufferedImage(1, 1, BufferedImage.TYPE_INT_RGB).createGraphics();
        try {
            var metricas = medidor.getFontMetrics(fonteLegenda);
            var linhas = new ArrayList<String>();
            paragrafos.forEach(paragrafo -> linhas.addAll(quebrar(paragrafo, metricas, larguraMaxima)));
            return linhas;
        } finally {
            medidor.dispose();
        }
    }

    private List<String> quebrar(String paragrafo, FontMetrics metricas, int larguraMaxima) {
        var linhas = new ArrayList<String>();
        var atual = new StringBuilder();
        for (var palavra : paragrafo.split(" ")) {
            var candidata = atual.isEmpty() ? palavra : atual + " " + palavra;
            if (metricas.stringWidth(candidata) > larguraMaxima && !atual.isEmpty()) {
                linhas.add(atual.toString());
                atual = new StringBuilder(palavra);
            } else {
                atual = new StringBuilder(candidata);
            }
        }
        if (!atual.isEmpty()) {
            linhas.add(atual.toString());
        }
        return linhas;
    }
}
