package br.sd.barragem.painel.infraestrutura.processos;

import br.sd.barragem.painel.aplicacao.porta.GerenciadorProcessos;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.File;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;

@Component
public class GerenciadorProcessosLocal implements GerenciadorProcessos {

    private final Path raiz;

    public GerenciadorProcessosLocal(@Value("${laboratorio.raiz:.}") String raiz) {
        this.raiz = Path.of(raiz).toAbsolutePath().normalize();
    }

    @Override
    public void iniciarControlador(int id) {
        Path script = raiz.resolve("scripts").resolve("iniciar-componente.ps1");
        ProcessBuilder construtor;
        if (System.getProperty("os.name").toLowerCase().contains("win") && Files.exists(script)) {
            construtor = new ProcessBuilder("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    script.toString(), "-Componente", "controlador", "-Perfil", "c" + id);
        } else {
            File log = raiz.resolve("logs").resolve("controlador-c" + id + ".log").toFile();
            log.getParentFile().mkdirs();
            construtor = new ProcessBuilder("java", "-jar", "middleware/controlador/target/controlador.jar",
                    "--spring.profiles.active=c" + id).redirectErrorStream(true).redirectOutput(log);
        }
        try {
            construtor.directory(raiz.toFile()).start();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
